#!/usr/bin/env bash
export REPOSITORY_PREFIX=${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com

aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${REPOSITORY_PREFIX}

aws ecr create-repository --repository-name python-petclinic-billing-service --region ${REGION} --no-cli-pager || true
docker build -t billing-service ./pet_clinic_billing_service --no-cache
docker tag billing-service:latest ${REPOSITORY_PREFIX}/python-petclinic-billing-service:latest
docker tag billing-service:latest ${REPOSITORY_PREFIX}/python-petclinic-billing-service:${COMMIT_SHA}
docker push ${REPOSITORY_PREFIX}/python-petclinic-billing-service:latest
docker push ${REPOSITORY_PREFIX}/python-petclinic-billing-service:${COMMIT_SHA}