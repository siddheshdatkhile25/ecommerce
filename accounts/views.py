from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from core.models import *
from django.contrib import messages
from django .contrib.auth import authenticate,login,logout
from django.views.decorators.csrf import requires_csrf_token

# Create your views here.
def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username,password=password)
        if user is not None :
            login(request,user)
            return redirect('/')
        messages.info(request,"Login Failed, Please check credential")

    return render(request,'accounts/login.html')

def user_register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone_field = request.POST.get('phone_field')

        #print(username,email,password,confirm_password,phone_field)
 
        if password == confirm_password :
            if User.objects.filter(username=username).exists():
                messages.info(request,"Username Already Exists")
                return redirect('user_register')

            else:
                if User.objects.filter(email=email).exists():
                    messages.info(request,"Email Already Exists")
                    return redirect('user_register')
                else:
                    user = User.objects.create_user(username=username,email=email,password=password)
                    user.save()
                    data = Customer(user=user,phone_field=phone_field)
                    data.save()


                    # code for login of user will come here 

                    our_user = authenticate(username=username,password=password)
                    if our_user is not None :
                        login(request,user)
                        return redirect('/')
        
        else :
            messages.info(request,"Password and confirm password mismatch !")
            return redirect('user_register')

    return render(request,'accounts/register.html')

def user_logout(request):
    logout(request)
    return redirect('/')