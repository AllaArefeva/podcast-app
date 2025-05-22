gcloud run deploy podcast-app \
--source src \
--region $GOOGLE_CLOUD_LOCATION \
--platform managed \
--min-instances 0 \
--max-instances 5 \
--cpu 2 \
--memory 2048Mi \
--timeout 120 \
--session-affinity \
--set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI \
--allow-unauthenticated

