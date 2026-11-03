from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    user = authenticate(
        username=str(request.data.get('username', '')).lower().strip(),
        password=request.data.get('password', ''),
    )

    if not user:
        return Response(
            {'error': 'نام کاربری یا رمز اشتباه است'},
            status=400
        )

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'username': user.username
    })
