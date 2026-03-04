from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            return Response(
                {
                    "status": "ok",
                    "database": "ok",
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {
                    "status": "error",
                    "database": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
