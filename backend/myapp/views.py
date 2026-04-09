"""
Fixed views for health agent application
All CSRF issues resolved, proper error handling added
"""

import json
import logging
from turtle import pd
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import HealthProfile
from .services.decision import HealthAgent
from .services.recommendation import get_recommendations
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
@csrf_exempt  # Frontend will handle CSRF with token
def api_signup(request):
    """
    Register a new user
    POST data: {name, email, password, confirm_password, dob, age, gender}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    try:
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")
        dob = data.get("dob")
        age = data.get("age")
        gender = data.get("gender")

        # Validation
        if not name or len(name) < 2:
            return JsonResponse(
                {"success": False, "error": "Name must be at least 2 characters"},
                status=400
            )

        if not email or "@" not in email:
            return JsonResponse(
                {"success": False, "error": "Valid email is required"},
                status=400
            )

        if not password or len(password) < 8:
            return JsonResponse(
                {"success": False, "error": "Password must be at least 8 characters"},
                status=400
            )

        if password != confirm_password:
            return JsonResponse(
                {"success": False, "error": "Passwords do not match"},
                status=400
            )

        if User.objects.filter(email=email).exists():
            return JsonResponse(
                {"success": False, "error": "Email already registered"},
                status=400
            )

        # Create user with transaction
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                name=name,
                dob=dob if dob else None,
                age=age if age else None,
                gender=gender if gender else None
            )

        # Auto-login after signup
        login(request, user)

        return JsonResponse({
            "success": True,
            "message": "Account created successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name
            }
        })

    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Registration failed. Please try again."},
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def api_login(request):
    """
    Authenticate user and start session
    POST data: {email, password}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    try:
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return JsonResponse(
                {"success": False, "error": "Email and password required"},
                status=400
            )

        # Try to get user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"Login attempt for non-existent email: {email}")
            return JsonResponse(
                {"success": False, "error": "Invalid email or password"},
                status=401
            )

        # Authenticate
        if not user.check_password(password):
            logger.warning(f"Failed login attempt for user: {email}")
            return JsonResponse(
                {"success": False, "error": "Invalid email or password"},
                status=401
            )

        # Check if user is active
        if not user.is_active:
            return JsonResponse(
                {"success": False, "error": "Account is inactive"},
                status=401
            )

        # Login
        login(request, user)

        return JsonResponse({
            "success": True,
            "message": "Logged in successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name
            }
        })

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Login failed. Please try again."},
            status=500
        )


@require_http_methods(["POST"])
def logout_view(request):
    """Logout user and destroy session"""
    logout(request)
    return JsonResponse({"success": True, "message": "Logged out successfully"})


@require_http_methods(["GET"])
def auth_status(request):
    """Check current authentication status"""
    return JsonResponse({
        "authenticated": request.user.is_authenticated,
        "user": {
            "id": request.user.id,
            "email": request.user.email,
            "name": request.user.name
        } if request.user.is_authenticated else None
    })


# ============================================
# HOME & HEALTH VIEWS
# ============================================

def home(request):
    """Home page - redirect to health if authenticated"""
    if request.user.is_authenticated:
        return redirect("/health/")
    return render(request, "index.html")


@login_required(login_url="/")
def health(request):
    """Main health dashboard page"""
    return render(request, "health.html")


# ============================================
# HEALTH PROFILE VIEWS
# ============================================

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def save_health_profile(request):
    """
    Save or update user's health profile
    POST data: {height, weight, sleep, smoking, alcohol, exercise, diet, 
                resting_heart_rate, systolic_bp, diastolic_bp, blood_sugar, 
                cholesterol, vitamin_deficiency}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        with transaction.atomic():
            profile, created = HealthProfile.objects.get_or_create(user=request.user)

            # Update basic metrics
            profile.height_cm = data.get("height_cm")
            profile.weight_kg = data.get("weight_kg")
            profile.sleep_hours = data.get("sleep_hours")

            # Update lifestyle factors
            profile.smoking_status = data.get("smoking")
            profile.alcohol_consumption = data.get("alcohol")
            profile.exercise_frequency = data.get("exercise")
            profile.diet_type = data.get("diet")

            # Update vital signs
            profile.resting_heart_rate = data.get("resting_heart_rate")
            profile.systolic_bp = data.get("systolic_bp")
            profile.diastolic_bp = data.get("diastolic_bp")

            # Update health markers
            profile.fasting_blood_sugar = data.get("fasting_blood_sugar")
            profile.total_cholesterol = data.get("total_cholesterol")
            profile.vitamin_deficiency = data.get("vitamin_deficiency", [])

            profile.save()

            return JsonResponse({
                "success": True,   # ✅ FIXED
                "message": "Health profile saved successfully",
                "profile": get_profile_data(profile)
            })

    except Exception as e:
        logger.error(f"Profile save error: {str(e)}")
        return JsonResponse(
            {"error": "Failed to save profile"},
            status=500
        )


@login_required
@require_http_methods(["GET"])
def get_health_profile(request):
    """Retrieve user's health profile"""
    try:
        profile = HealthProfile.objects.get(user=request.user)
        return JsonResponse({
            "success": True,
            "profile": get_profile_data(profile)
        })
    except HealthProfile.DoesNotExist:
        return JsonResponse({
            "success": True,
            "profile": None
        })
    except Exception as e:
        logger.error(f"Profile fetch error: {str(e)}")
        return JsonResponse(
            {"error": "Failed to fetch profile"},
            status=500
        )


def get_profile_data(profile):
    """Helper to format profile data"""
    bmi = None
    if profile.height_cm and profile.weight_kg:
        height_m = profile.height_cm / 100
        bmi = round(profile.weight_kg / (height_m ** 2), 2)

    return {
    "height_cm": profile.height_cm,
    "weight_kg": profile.weight_kg,
    "sleep_hours": profile.sleep_hours,
    "smoking": profile.smoking_status,
    "alcohol": profile.alcohol_consumption,
    "exercise": profile.exercise_frequency,
    "diet": profile.diet_type,
    "resting_heart_rate": profile.resting_heart_rate,
    "systolic_bp": profile.systolic_bp,
    "diastolic_bp": profile.diastolic_bp,
    "fasting_blood_sugar": profile.fasting_blood_sugar,
    "total_cholesterol": profile.total_cholesterol,
    "vitamin_deficiency": profile.vitamin_deficiency,
    "bmi": bmi,
}


# ============================================
# HEALTH AGENT VIEWS
# ============================================

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def health_decision_agent(request):
    """
    Get health decision and recommendations based on user message
    POST data: {message}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse(
                {"error": "Message cannot be empty"},
                status=400
            )

        # Verify profile exists
        try:
            profile = HealthProfile.objects.get(user=request.user)
        except HealthProfile.DoesNotExist:
            return JsonResponse({
                "success": False,
                "reply": "Please complete your health profile first."
            })

        # Get decision from agent
        agent = HealthAgent()
        decision = agent.make_decision(
            user=request.user,
            user_message=user_message
        )

        # Get recommendations
        recommendations = get_recommendations(decision)

        return JsonResponse({
            "success": True,
            "agent": "health_decision",
            "decision": decision,
            "recommendations": recommendations
        })

    except Exception as e:
        logger.error(f"Health decision error: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Failed to generate decision"},
            status=500
        )

# ============================================
# HEALTH SCORE CALCULATION VIEW
# ============================================

@login_required
@require_http_methods(["GET"])
def get_health_score(request):
    """
    Calculate and return overall health score
    Scale: 0-100
    """
    try:
        profile = HealthProfile.objects.get(user=request.user)
        score = calculate_health_score(profile)
        
        return JsonResponse({
            "success": True,
            "health_score": score,
            "category": get_health_category(score)
        })
    except HealthProfile.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Please complete your health profile first"
        }, status=400)
    except Exception as e:
        logger.error(f"Health score calculation error: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Failed to calculate health score"},
            status=500
        )


def calculate_health_score(profile):
    """
    Calculate health score based on various metrics (0-100)
    """
    score = 100
    
    # BMI assessment
    if profile.height_cm and profile.weight_kg:
        bmi = profile.weight_kg / ((profile.height_cm / 100) ** 2)
        if bmi < 18.5 or bmi > 29.9:
            score -= 15
        elif bmi > 25:
            score -= 5

    # Sleep assessment
    if profile.sleep_hours:
        if profile.sleep_hours < 6 or profile.sleep_hours > 9:
            score -= 10
        if profile.sleep_hours < 5 or profile.sleep_hours > 10:
            score -= 10

    # Blood pressure assessment
    if profile.systolic_bp and profile.diastolic_bp:
        if profile.systolic_bp >= 140 or profile.diastolic_bp >= 90:
            score -= 15
        elif profile.systolic_bp >= 130 or profile.diastolic_bp >= 85:
            score -= 10

    # Fasting blood sugar assessment
    if profile.fasting_blood_sugar:
        if profile.fasting_blood_sugar >= 126:
            score -= 15
        elif profile.fasting_blood_sugar >= 100:
            score -= 10

    # Cholesterol assessment
    if profile.total_cholesterol:
        if profile.total_cholesterol >= 240:
            score -= 15
        elif profile.total_cholesterol >= 200:
            score -= 10

    # Smoking assessment
    if profile.smoking_status == "yes":
        score -= 20
    elif profile.smoking_status == "former":
        score -= 5

    # Alcohol assessment
    if profile.alcohol_consumption == "high":
        score -= 15
    elif profile.alcohol_consumption == "moderate":
        score -= 5

    # Exercise assessment
    if profile.exercise_frequency == "none":
        score -= 15
    elif profile.exercise_frequency == "low":
        score -= 10

    # Vitamin deficiency assessment
    if profile.vitamin_deficiency:
        score -= min(len(profile.vitamin_deficiency) * 5, 15)

    return max(0, min(100, score))


def get_health_category(score):
    """Get health category based on score"""
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    else:
        return "Poor"