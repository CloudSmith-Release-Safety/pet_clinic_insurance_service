from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Insurance, PetInsurance
from .serializers import InsuranceSerializer, PetInsuranceSerializer
from .rest import generate_billings
import logging

logger = logging.getLogger(__name__)

class InsuranceViewSet(viewsets.ModelViewSet):
    queryset = Insurance.objects.all()
    serializer_class = InsuranceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not queryset:
            return Response({"error": "Not Found", "message": "No insurance records found"}, status=status.HTTP_404_NOT_FOUND)
        return queryset


class PetInsuranceViewSet(viewsets.ModelViewSet):
    queryset = PetInsurance.objects.all()
    serializer_class = PetInsuranceSerializer
    lookup_field = 'pet_id'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        owner_id = request.data.get('owner_id')
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer, owner_id)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        owner_id = request.data.get('owner_id')

        if serializer.is_valid():
            self.perform_update(serializer, owner_id)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer, owner_id):
        serializer.save()
        if owner_id:
            generate_billings(serializer.data, owner_id, "insurance", serializer.data.get("insurance_name"))
            logger.info(f"Generated billing for owner {owner_id}, pet {serializer.data.get('pet_id')}")
        else:
            logger.warning("No owner_id provided, skipping billing generation")
    def send_update_notification(self, instance):
        # Your custom logic to send a notification
        # after the instance is updated
        pass

    def get_queryset(self):
        queryset = super().get_queryset()
        if not queryset:
            return []  # Return an empty list if the queryset is empty
        return queryset

class HealthViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message':'ok'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def create_claim(request):
    """Create a new insurance claim in DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        table = dynamodb.Table('InsuranceClaims')
        
        claim_data = {
            'claimId': request.data.get('claim_id'),
            'ownerId': request.data.get('owner_id'),
            'petId': request.data.get('pet_id'),
            'amount': request.data.get('amount'),
            'status': 'pending'
        }
        
        table.put_item(Item=claim_data)
        return Response(claim_data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
