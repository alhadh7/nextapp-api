# import jwt

# token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQzNzY4MzQxLCJpYXQiOjE3NDM3NjY1NDEsImp0aSI6IjNmNjRlZjdmNDc2MzRiNDM4NzlhYWIzMTlkMDAzMjY2IiwidXNlcl9pZCI6OX0.mLsej08Led-5CFNSAF8zqt6L0ghZ7PZBsowb47qyxlo"
# decoded = jwt.decode(token, "123", algorithms=["HS256"])
# print(decoded)

from authentication.serializers import CustomTokenObtainPairSerializer
print(CustomTokenObtainPairSerializer)
