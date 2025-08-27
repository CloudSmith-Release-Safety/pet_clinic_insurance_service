from py_eureka_client import eureka_client
from opentelemetry import trace
import requests
import logging
import json
import os

logger = logging.getLogger(__name__)

# Configuration for service URLs - depends on externalized configuration
CUSTOMERS_SERVICE_URL = os.getenv('CUSTOMERS_SERVICE_URL', 'http://customers-service')
BILLING_SERVICE_URL = os.getenv('BILLING_SERVICE_URL', 'http://billing-service')

def resolve_service_url(service_name):
    """
    Resolve service URL using environment configuration or fallback to Eureka discovery
    This method now supports the new externalized configuration approach
    """
    # Use environment-specific URLs if available
    if service_name == "customers-service" and CUSTOMERS_SERVICE_URL:
        return CUSTOMERS_SERVICE_URL.rstrip('/') + '/'
    elif service_name == "billing-service" and BILLING_SERVICE_URL:
        return BILLING_SERVICE_URL.rstrip('/') + '/'
    
    # Fallback to Eureka discovery for backward compatibility
    try:
        client = eureka_client.get_client()
        instances = client.applications.get_application(service_name.upper()).instances
        logger.info(f"Found {len(instances)} instances for {service_name}")
        if len(instances) > 0:
            instance = instances[0]
            return 'http://' + instance.ipAddr + ":" + str(instance.port.port) + "/"
        else:
            raise ValueError(f"No valid instance found for service '{service_name}'")
    except Exception as e:
        logger.error(f"Service discovery failed for {service_name}: {e}")
        raise

def get_owner_info(owner_id):
    """
    Get owner information using the new configurable service URL
    """
    trace.get_current_span().set_attribute("customer.id", owner_id)
    server_url = resolve_service_url("customers-service")
    
    # Updated endpoint path to match new API gateway configuration
    endpoint_url = f"{server_url}owners/{owner_id}"
    logger.info(f"Fetching owner info from: {endpoint_url}")
    
    try:
        response = requests.get(endpoint_url)
        logger.info(f"Owner info response: {endpoint_url} - {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.text)
            logger.info(f"Owner data retrieved: {data}")
            return data
        else:
            logger.error(f"Failed to get owner info: {response.status_code}")
            raise ValueError(f"Owner {owner_id} not found")
    except requests.RequestException as e:
        logger.error(f"Request failed for owner {owner_id}: {e}")
        raise

def create_billings(url, data):
    logger.info(f"Creating billing: {data}")
    response = requests.post(url, json=data)
    logger.info(f"Create billing response: {url} - {response.status_code}")

def update_billings(url, data):
    logger.info(f"Updating billing: {data}")
    response = requests.put(url, json=data)
    logger.info(f"Update billing response: {url} - {response.status_code}")

def generate_billings(pet_insurance, owner_id, type, type_name):
    """
    Generate billings using the new configurable service URLs
    """
    server_url = resolve_service_url("billing-service")
    pet_id = pet_insurance["pet_id"]
    url = f"{server_url}billings/{owner_id}/{pet_id}/{type}/"
    
    try:
        response = requests.get(url)
        logger.info(f"Billing check: {url} - {response.status_code}")
        
        if response.status_code != 200:
            logger.info("Creating new billing record")
            create_billings(f"{server_url}billings/", {
                "owner_id": owner_id,
                "type": type,
                "type_name": type_name,
                "pet_id": pet_id,
                "payment": pet_insurance["price"],
                "status": "open"
            })
        else:
            logger.info("Updating existing billing record")
            data = json.loads(response.text)
            data['payment'] = pet_insurance["price"]
            update_billings(f"{server_url}billings/{data['id']}/", data)
    except requests.RequestException as e:
        logger.error(f"Billing operation failed: {e}")
        raise

