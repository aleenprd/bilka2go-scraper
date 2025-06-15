#!/bin/sh

# Authenticating via Workload Identity Federation
# https://github.com/marketplace/actions/authenticate-to-google-cloud#setup

# Export environment variables default values
PROJECT_ID="my-project-id"
WORKLOAD_IDENTITY_POOL="my-identity-pool" 
WORKLOAD_IDENTITY_POOL_DISPLAY_NAME="My Identity Pool"
WORKLOAD_IDENTITY_PROVIDER="my-identity-provider"
WORKLOAD_IDENTITY_PROVIDER_DISPLAY_NAME="My Identity Provider"
SERVICE_ACCOUNT="my-service-account"
REPO="myname/myrepo"
LOCATION="global"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --project-id)
      PROJECT_ID=$2
      shift
      ;;
    --workload-identity-pool)
      WORKLOAD_IDENTITY_POOL=$2
      shift
      ;;
    --workload-identity-pool-display-name)
      WORKLOAD_IDENTITY_POOL_DISPLAY_NAME=$2
      shift
      ;;
    --workload-identity-provider)
      WORKLOAD_IDENTITY_PROVIDER=$2
      shift
      ;;
    --workload-identity-provider-display-name)
      WORKLOAD_IDENTITY_PROVIDER_DISPLAY_NAME=$2
      shift
      ;;
    --service-account)
      SERVICE_ACCOUNT=$2
      shift
      ;;
    --repo)
      REPO=$2
      shift
      ;;
    --location)
      LOCATION=$2
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
  shift
done

# Assign default values if not provided
PROJECT_ID="${PROJECT_ID:-$DEFAULT_PROJECT_ID}"
WORKLOAD_IDENTITY_POOL="${WORKLOAD_IDENTITY_POOL:-$DEFAULT_WORKLOAD_IDENTITY_POOL}"
WORKLOAD_IDENTITY_POOL_DISPLAY_NAME="${WORKLOAD_IDENTITY_POOL_DISPLAY_NAME:-$DEFAULT_WORKLOAD_IDENTITY_POOL_DISPLAY_NAME}"
WORKLOAD_IDENTITY_PROVIDER="${WORKLOAD_IDENTITY_PROVIDER:-$DEFAULT_WORKLOAD_IDENTITY_PROVIDER}"
WORKLOAD_IDENTITY_PROVIDER_DISPLAY_NAME="${WORKLOAD_IDENTITY_PROVIDER_DISPLAY_NAME:-$DEFAULT_WORKLOAD_IDENTITY_PROVIDER_DISPLAY_NAME}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-$DEFAULT_SERVICE_ACCOUNT}"
REPO="${REPO:-$DEFAULT_REPO}"
LOCATION="${LOCATION:-$DEFAULT_LOCATION}"

# Export environment variables
export PROJECT_ID
export WORKLOAD_IDENTITY_POOL
export WORKLOAD_IDENTITY_POOL_DISPLAY_NAME
export WORKLOAD_IDENTITY_PROVIDER
export WORKLOAD_IDENTITY_PROVIDER_DISPLAY_NAME
export SERVICE_ACCOUNT
export REPO
export LOCATION

# (Optional) Create a Google Cloud Service Account. 
# If you already have a Service Account, take note of the email address and skip this step.
gcloud iam service-accounts create "${SERVICE_ACCOUNT}" \
  --project "${PROJECT_ID}"

# (Optional) Grant the Google Cloud Service Account permissions to Artifact Registry
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member=serviceAccount:"${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role=roles/artifactregistry.reader \
    --role=roles/artifactregistry.writer \
    --role=roles/bigquery.dataEditor \
    --role=roles/run.invoker \
    --role=roles/roles/storage.objectCreator \
    --role=roles/storage.insightsCollectorService \
    --role=roles/iam.serviceAccountTokenCreator

# Enable the IAM Credentials API:
gcloud services enable iamcredentials.googleapis.com \
  --project "${PROJECT_ID}"

# Create a Workload Identity Pool:
gcloud iam workload-identity-pools create "${WORKLOAD_IDENTITY_POOL}"  \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}" \
  --display-name="${WORKLOAD_IDENTITY_POOL_DISPLAY_NAME}"

# Get the full ID of the Workload Identity Pool:
export WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "${WORKLOAD_IDENTITY_POOL}" \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}" \
  --format="value(name)")

# Create a Workload Identity Provider in that pool:
gcloud iam workload-identity-pools providers create-oidc "${WORKLOAD_IDENTITY_PROVIDER}" \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}" \
  --workload-identity-pool="${WORKLOAD_IDENTITY_POOL}" \
  --display-name="${WORKLOAD_IDENTITY_PROVIDER_DISPLAY_NAME}" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow authentications from the Workload Identity Provider originating from your repository
# to impersonate the Service Account created above.
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${REPO}"

# Extract the Workload Identity Provider resource name:
export WORKLOAD_IDENTITY_PROVIDER_RESOURCE_NAME=$(gcloud iam workload-identity-pools providers describe "${WORKLOAD_IDENTITY_PROVIDER}" \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}" \
  --workload-identity-pool="${WORKLOAD_IDENTITY_POOL}" \
  --format="value(name)")
