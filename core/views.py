from django.shortcuts import render,redirect
from django.contrib import messages
from core.forms import CheckoutForm, ProductForm
from core.models import *
from django.utils import timezone
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.template.loader import get_template
from xhtml2pdf import pisa
from core.models import Order, CheckoutAddress


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_ID, settings.RAZORPAY_SECRET))


# Create your views here.

def index(request):
    products = Product.objects.all()
    return render(request, 'core/index.html',{'products':products})

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST,request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request,"Product has been added")
            return redirect('/')
        else:
            messages.info("Product is not Added!")
    else:
        form = ProductForm()
    return render(request,'core/add_product.html',{'form':form})
    

def shop(request):
    products = Product.objects.all()
    return render(request, 'core/shop.html',{'products':products})
    

def product_desc(request,pk):
    product = Product.objects.get(pk=pk)
    return render(request,'core/product_desc.html',{'product':product})

def add_to_cart(request, pk):
    product = Product.objects.get(pk=pk)
    
    order_item, created = OrderItem.objects.get_or_create(
        product=product,
        user=request.user,
        ordered=False,
    )

    #get query set of order object
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(product__pk=pk).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Added Quantity Item")
            return redirect("product_desc", pk=pk)
        else:
            order.items.add(order_item)
            messages.info(request, "Item added to Cart")
            return redirect("product_desc", pk=pk)

    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "Item added to Cart")
        return redirect("product_desc", pk=pk)

def orderlist(request):
    if Order.objects.filter(user=request.user, ordered=False).exists():
        order = Order.objects.get(user=request.user, ordered=False)
        return render(request, "core/orderlist.html", {"order": order})
    return render(request, "core/orderlist.html", {"message": "Your Cart is Empty"},) 


def add_item(request, pk):
    # Get that Partiuclar Product of id = pk
    product = Product.objects.get(pk=pk)

    # Create Order item
    order_item, created = OrderItem.objects.get_or_create(
        product=product,
        user=request.user,
        ordered=False,
    )

    # Get Query set of Order Object of Particular User
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(product__pk=pk).exists():
            if order_item.quantity < product.product_available_count:
                order_item.quantity += 1
                order_item.save()
                messages.info(request, "Added Quantity Item")
                return redirect("orderlist")
            else:
                messages.info(request, "Sorry! Product is out of Stock")
                return redirect("orderlist")
        else:
            order.items.add(order_item)
            messages.info(request, "Item added to Cart")
            return redirect("product_desc", pk=pk)

    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "Item added to Cart")
        return redirect("product_desc", pk=pk)


def remove_item(request, pk):
    item = get_object_or_404(Product, pk=pk)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False,
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(product__pk=pk).exists():
            order_item = OrderItem.objects.filter(
                product=item,
                user=request.user,
                ordered=False,
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order_item.delete()
            messages.info(request, "Item quantity was updated")
            return redirect("orderlist")
        else:
            messages.info(request, "This item is not in your cart")
            return redirect("orderlist")
    else:
        messages.info(request, "You Do not have any Order")
        return redirect("orderlist")

def checkout_page(request):
    if CheckoutAddress.objects.filter(user=request.user).exists():
        return render(request, "core/checkout_address.html", {"payment_allow": "allow"})
    
    if request.method == "POST":
        print("Saving must start")
        form = CheckoutForm(request.POST)
        if form.is_valid():
            street_address = form.cleaned_data.get("street_address")
            apartment_address = form.cleaned_data.get("apartment_address")
            country = form.cleaned_data.get("country")
            zip_code = form.cleaned_data.get("zip")

            checkout_address = CheckoutAddress(
                user=request.user,
                street_address=street_address,
                apartment_address=apartment_address,
                country=country,
                zip_code=zip_code,
            )
            checkout_address.save()
            print("It should render the summary page")
            return render(request, "core/checkout_address.html", {"payment_allow": "allow"})
    else:
        form = CheckoutForm()
        return render(request, "core/checkout_address.html", {"form": form})




def payment(request):
    try:
        order = Order.objects.get(user=request.user, ordered=False)
        address = CheckoutAddress.objects.get(user=request.user)
        order_amount = order.get_total_price()

        # Dummy payment logic - mark the order as paid without processing any payment
        order.ordered = True
        order.save()

        print("Order found. Rendering payment summary.")
        return render(
            request,
            "core/paymentsummaryrazorpay.html",
            {
                "order": order,
                "final_price": order_amount,
            },
        )
    except Order.DoesNotExist:
        print("Order not found")
        return HttpResponse("404 Error")
    except Exception as e:
        print("An unexpected error occurred:", e)
        return HttpResponse("An unexpected error occurred.")



from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from core.models import Order, CheckoutAddress

def invoice(request):
    try:
        # Retrieve the order object based on your logic
        order = Order.objects.get(user=request.user, ordered=True)
        checkout_address = CheckoutAddress.objects.get(user=request.user)
        
        # Pass the order and checkout_address objects to the template context
        context = {
            'order': order,
            'checkout_address': checkout_address,
        }
        
        return render(request, "invoice/invoice.html", context)
    except Order.DoesNotExist:
        return HttpResponse("Order not found")
    except Exception as e:
        return HttpResponse("An unexpected error occurred: " + str(e))


@csrf_exempt
def handlerequest(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get("razorpay_payment_id", "")
            order_id = request.POST.get("razorpay_order_id", "")
            signature = request.POST.get("razorpay_signature", "")
            print(payment_id, order_id, signature)
            params_dict = {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }

            try:
                order_db = Order.objects.get(razorpay_order_id=order_id)
                print("Order Found")
            except:
                print("Order Not found")
                return HttpResponse("505 Not Found")
            order_db.razorpay_payment_id = payment_id
            order_db.razorpay_signature = signature
            order_db.save()
            print("Working............")
            result = razorpay_client.utility.verify_payment_signature(params_dict)
            if result == None:
                print("Working Final Fine............")
                amount = order_db.get_total_price()
                amount = amount * 100  # we have to pass in paisa
                payment_status = razorpay_client.payment.capture(payment_id, amount)
                if payment_status is not None:
                    print(payment_status)
                    order_db.ordered = True
                    order_db.save()
                    print("Payment Success")
                    checkout_address = CheckoutAddress.objects.get(user=request.user)
                    request.session[
                        "order_complete"
                    ] = "Your Order is Successfully Placed, You will receive your order within 5-7 working days"
                    return render(request, "invoice/invoice.html",{"order":order_db,"payment_status":payment_status,"checkout_address":checkout_address})
                else:
                    print("Payment Failed")
                    order_db.ordered = False
                    order_db.save()
                    request.session[
                        "order_failed"
                    ] = "Unfortunately your order could not be placed, try again!"
                    return redirect("/")
            else:
                order_db.ordered = False
                order_db.save()
                return render(request, "core/paymentfailed.html")
        except:
            return HttpResponse("Error Occured")

def invoice(request):
    return render(request, "invoice/invoice.html")


