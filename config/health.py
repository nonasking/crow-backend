from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer


class HealthCheckAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    renderer_classes = [JSONRenderer]

    def get(self, request):
        try:
            return Response(
                {
                    "status": "ok",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": "error", "info": f"{e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
