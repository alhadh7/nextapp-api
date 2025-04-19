# Health Connect API Documentation

This documentation provides details for the Health Connect API, which offers endpoints for user and partner registration, verification, login, logout, and booking management.

## Table of Contents
- [User Management](#user-management)
- [Partner Management](#partner-management)
- [Service Management](#service-management)
- [Booking Management](#booking-management)
- [Session Management](#session-management)
- [Variables](#variables)
- [Event Scripts](#event-scripts)


## User Management

### Register User
Creates a new user account.

- **URL:** `{{base_url}}/auth/register/user/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543210",
  "email": "user@example.com",
  "full_name": "John Doe"
}
```

### Verify User OTP
Verifies the OTP sent during user registration.

- **URL:** `{{base_url}}/auth/verify/user/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543210",
  "verification_id": "123456",
  "otp": "123456"
}
```

### User Login (Request OTP)
Requests an OTP for user login.

- **URL:** `{{base_url}}/auth/login/user/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543210"
}
```

### Verify User Login OTP
Verifies the OTP sent during user login.

- **URL:** `{{base_url}}/auth/verify/login/user/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543210",
  "verification_id": "123456",
  "otp": "123456"
}
```

### User Home
Retrieves the user's home page data.

- **URL:** `{{base_url}}/user/home/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

## Partner Management

### Register Partner
Creates a new partner account.

- **URL:** `{{base_url}}/auth/register/partner/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543211",
  "email": "partner@example.com",
  "full_name": "Dr. Smith",
  "education": "MBBS",
  "experience": "10"
}
```

### Register Partner (with Medical Certificate)
Creates a new partner account with medical certificate upload.

- **URL:** `{{base_url}}/auth/register/partner/`
- **Method:** `POST`
- **Body:** `form-data`
  - `phone_number`: "9876543211"
  - `email`: "partner@example.com"
  - `full_name`: "Dr. Smith"
  - `education`: "MBBS"
  - `experience`: "10"
  - `medical_certificate`: [file upload]

### Verify Partner OTP
Verifies the OTP sent during partner registration.

- **URL:** `{{base_url}}/auth/verify/partner/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543211",
  "verification_id": "123456",
  "otp": "123456"
}
```

### Partner Login (Request OTP)
Requests an OTP for partner login.

- **URL:** `{{base_url}}/auth/login/partner/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543211"
}
```

### Verify Partner Login OTP
Verifies the OTP sent during partner login.

- **URL:** `{{base_url}}/auth/verify/login/partner/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "phone_number": "9876543211",
  "verification_id": "123456",
  "otp": "123456"
}
```

### Partner Home
Retrieves the partner's home page data.

- **URL:** `{{base_url}}/partner/home/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Get Booking Details for Partner
Retrieves details of a specific booking for a partner.

- **URL:** `{{base_url}}/partner/bookings/{{booking_id}}/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Book Slot
Allows a partner to book available time slots.

- **URL:** `{{base_url}}/partner/book-slot/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:**
```json
{
  "slots": [
    {
      "date": "2025-04-08",
      "start_time": "09:00",
      "end_time": "11:00"
    },
    {
      "date": "2025-04-08",
      "start_time": "11:00",
      "end_time": "13:00"
    }
  ]
}
```

### Get Available Bookings
Retrieves a list of available bookings for a partner.

- **URL:** `{{base_url}}/partner/bookings/available/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Accept Booking
Allows a partner to accept a booking.

- **URL:** `{{base_url}}/partner/bookings/{{booking_id}}/accept/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:** `{}`

### Get Active Bookings
Retrieves a list of active bookings for a partner.

- **URL:** `{{base_url}}/partner/bookings/active/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Toggle Work Status
Allows a partner to toggle the status of a booking.

- **URL:** `{{base_url}}/partner/bookings/{{booking_id}}/toggle-status/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:** `{}`

### Respond to Extension Request
Allows a partner to respond to a booking extension request.

- **URL:** `{{base_url}}/partner/extensions/{{extension_id}}/respond/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:**
```json
{
  "response": "approve"
}
```

### Get Completed Bookings
Retrieves a list of completed bookings for a partner.

- **URL:** `{{base_url}}/partner/bookings/completed/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Get Partner Reviews
Retrieves a list of reviews for a partner.

- **URL:** `{{base_url}}/partner/reviews/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

## Service Management

### Get Service Types
Retrieves a list of available service types.

- **URL:** `{{base_url}}/user/services/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

## Booking Management

### Create Booking
Creates a new booking.

- **URL:** `{{base_url}}/user/bookings/create/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:**
```json
{
  "service_type": 1,
  "partner_type": "trained",
  "is_instant": true,
  "hours": 4,
  "user_location": "123 Main Street, Anytown",
  "hospital_location": "General Hospital, Anytown"
}
```

### Get Booking Details
Retrieves details of a specific booking.

- **URL:** `{{base_url}}/user/bookings/{{booking_id}}/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Get Available Partners
Retrieves a list of available partners for a booking.

- **URL:** `{{base_url}}/user/bookings/{{booking_id}}/available-partners/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Select Partner
Selects a partner for a booking.

- **URL:** `{{base_url}}/user/bookings/{{booking_id}}/select-partner/{{partner_id}}/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`

### Create Booking Order
Creates an order for a booking.

- **URL:** `{{base_url}}/user/bookings/{{booking_id}}/create-order/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`

### Process Booking Payment
Processes payment for a booking.

- **URL:** `{{base_url}}/user/bookings/{{booking_id}}/process-payment/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`

### Create Extension Order
Creates an order for a booking extension.

- **URL:** `{{base_url}}/user/extensions/{{extension_id}}/create-order/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`

### Process Extension Payment
Processes payment for a booking extension.

- **URL:** `{{base_url}}/user/extensions/{{extension_id}}/process-payment/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`

### Get Active Bookings
Retrieves a list of active bookings for a user.

- **URL:** `{{base_url}}/user/bookings/active/`
- **Method:** `GET`
- **Headers:** `Authorization: Bearer {{access_token}}`

### Request Booking Extension
Requests an extension for a booking.

- **URL:** `{{base_url}}/user/bookings/{{booking_id}}/extension/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:**
```json
{
  "additional_hours": 2
}
```

### Create Review
Creates a review for a completed booking.

- **URL:** `{{base_url}}/user/bookings/{{booking_id}}/review/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:**
```json
{
  "rating": 5,
  "comment": "Excellent service! Very professional and helpful."
}
```

## Session Management

### Token Refresh
Refreshes an expired access token.

- **URL:** `{{base_url}}/auth/token/refresh/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "refresh": "{{refresh_token}}"
}
```

### Token Verify
Verifies the validity of an access token.

- **URL:** `{{base_url}}/auth/token/verify/`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
  "token": "{{access_token}}"
}
```

### Logout
Logs out a user or partner.

- **URL:** `{{base_url}}/auth/logout/`
- **Method:** `POST`
- **Headers:** 
  - `Authorization: Bearer {{access_token}}`
  - `Content-Type: application/json`
- **Body:**
```json
{
  "refresh": "{{refresh_token}}"
}
```

## Variables

The following variables are used in the collection:

| Variable | Default Value | Type | Description |
|----------|---------------|------|-------------|
| base_url | http://127.0.0.1:8000 | string | Base URL for all API requests |
| access_token | | string | JWT access token for authentication |
| refresh_token | | string | JWT refresh token for refreshing expired access tokens |
| booking_id | | string | ID of a booking |
| partner_id | | string | ID of a partner |
| request_id | | string | ID of a request |
| extension_id | | string | ID of a booking extension |

## Event Scripts

The collection includes a test script that automatically saves `access_token` and `refresh_token` values from API responses to environment variables:

```javascript
if (pm.response.code === 200 || pm.response.code === 201) {
    const jsonData = pm.response.json();
    if (jsonData.access) {
        pm.environment.set('access_token', jsonData.access);
        console.log('Access token saved to environment');
    }
    if (jsonData.refresh) {
        pm.environment.set('refresh_token', jsonData.refresh);
        console.log('Refresh token saved to environment');
    }
}
```
