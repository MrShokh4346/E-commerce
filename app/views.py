from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from .models import Item, OrderItem, Order,  Payment, Coupon, Refund, Address  
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm
import stripe
import string
import random
# Create your views here.


stripe.api_key = settings.STRIPE_SECRET_KEY


def is_valid_form(values):
    valid = True
    for field in values:
        if field == "":
            valid = False
    return valid

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

class HomeView(ListView):
    model = Item
    paginate_by = 4
    template_name = 'home-page.html'


class DetailView(DetailView):
    model = Item
    template_name = 'product-page.html'


class OrderSummary(LoginRequiredMixin,View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                "object":order
            }
            return render(self.request,'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request,"You do not have an active order")
            redirect('/')
        

class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                "order":order,
                "DISPLAY_COUPON_FORM":False
            }
            return render(self.request, 'payment.html', context)
        else:
            messages.warning(self.request,"You have not added a billing address")
            return redirect('checkout')

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get("stripeToken")
        amount = int(order.get_total * 100)
        
        try:
            charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        source=token,
                        # customer=userprofile.stripe_customer_id
                    )
            
            payment = Payment()
            payment.stripe_charge_id = charge
            payment.user = self.request.user
            payment.amount = order.get_total * 100
            payment.save()
          

            order.ordered = True
            order.ref_code = create_ref_code
            order.payment = payment
            order.save()
            messages.success(self.request, "Your order was succesful")
            return redirect("/")
        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.warning(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate limit error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parametzers were supplied to Stripe's API
            print(e)
            messages.warning(self.request, "Invalid parameters")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, "Not authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, "Network error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(
                self.request, "Something went wrong. You were not charged. Please try again.")
            return redirect("/")

        except Exception as e:
            # send an email to ourselves
            messages.warning(
                self.request, "A serious error occurred. We have been notifed.")
            return redirect("/")

  

# def item_litemplate_nast(request):
#     context = {
#         'items': Item.objects.all()
#     }
#     return render(request, 'home-page.html', context)

class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                "form":form,
                'couponform':CouponForm(),
                'order':order,
                'DISPLAY_COUPON_FORM':True
            }

            shipping_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'S',
                default = True
            )

            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_addtess':shipping_address_qs[0]}
                )

            billing_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'S',
                default = True
            )

            if billing_address_qs.exists():
                context.update(
                    {'default_billing_addtess':billing_address_qs[0]}
                )

            return render(self.request, "checkout-page.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request,"You do not have an active cart")
            return redirect("checkout")
            
        
    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        # print(form.cleaned_data)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                
                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    print('use_default_shipping')
                    addres_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'S',
                        default = True
                    )
                    if addres_qs:
                        shipping_address = addres_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(self.request, "No shipping addres available")
                        return redirect('checkout')
                else:
                    print("User is entring a new shipping addres")
                    shipping_address1 = self.request.POST.get("shipping_address")
                    shipping_address2 = self.request.POST.get("shipping_address2")
                    shipping_country = self.request.POST.get("shipping_country")
                    shipping_zip = self.request.POST.get("shipping_zip")
                    
                    shipping_values = [shipping_address1, shipping_country, shipping_zip]
                    
                    if is_valid_form(shipping_values):
                        shipping_address = Address(
                            user = self.request.user,
                            street_address = shipping_address1,
                            appatrment_address = shipping_address2,
                            country = shipping_country,
                            zip = shipping_zip,
                            address_type = 'S'
                        )
                        shipping_address.save()
                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_address.defau = True
                            shipping_address.save()

                    else:
                        messages.info(self.request, "Please fill in the required shipping addres fields")


                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')
                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print('use_default_billing')
                    addres_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'B',
                        default = True
                    )
                    if addres_qs:
                        billing_address = addres_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, "No billing addres available")
                        return redirect('checkout')
                else:
                    print("User is entring a new billing addres")
                    billing_address1 = self.request.POST.get("billing_address")
                    billing_address2 = self.request.POST.get("billing_address2")
                    billing_country = self.request.POST.get("billing_country")
                    billing_zip = self.request.POST.get("billing_zip")
                    
                    billing_values = [billing_address1, billing_country, billing_zip]
                    
                    if is_valid_form(billing_values):
                        billing_address = Address(
                            user = self.request.user,
                            street_address = shipping_address1,
                            appatrment_address = shipping_address2,
                            country = shipping_country,
                            zip = shipping_zip,
                            address_type = 'B'
                        )
                        billing_address.save()
                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_address.defau = True
                            billing_address.save()

                    else:
                        messages.info(self.request, "Please fill in the required billing addres fields")


                payment_option = self.request.POST.get("payment_option")


                if payment_option == "S":
                    return redirect("payment", payment_option="stripe")
                elif payment_option == "P":
                    return redirect("payment", payment_option="paypal")
                else:
                    messages.warning(self.request, "Invali payment opyion selected")
                    return redirect("checkout")
            else:
                messages.warning(self.request, "Invalid form")
                return redirect('/')
        except ObjectDoesNotExist:
            messages.warning(self.request,"You do not have an active order")
            return redirect('order_summary')
        
        
           
        

# def product(request):
#     return render(request, 'product-page.html')

@login_required
def add_to_card(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ordered_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False
            )
    order_qs = Order.objects.filter(
            user=request.user, 
            ordered=False
            )
    print("\n1\n")
    print(order_qs)
    print("\n1\n")
    if order_qs.exists():
        order = order_qs.last()
        if order.items.filter(item__slug=item.slug).exists():
            ordered_item.quantity += 1
            ordered_item.save()
            messages.info(request,"This item quantity was updated")
        else:
            messages.info(request,"This item was added  to your cart")
            order.items.add(ordered_item)
            return redirect("order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(ordered_item)
        messages.info(request,"This item was added  to your cart")
    return redirect("order-summary")

@login_required
def remove_from_card(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
            user=request.user, 
            ordered=False
            )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            ordered_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(ordered_item)
            ordered_item.delete()
            messages.info(request,"This item was removed from your cart")
            return redirect("order-summary") 
        else:
            messages.info(request,"This item was not your cart")
            return redirect("order-summary")
    else:
        messages.info(request,"You do not have an active cart")
        return redirect("order-summary")
    


@login_required
def remove_single_item_from_card(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ordered_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False
            )
    order_qs = Order.objects.filter(
            user=request.user, 
            ordered=False
            )
    if order_qs.exists():
        order = order_qs.last()
        if order.items.filter(item__slug=item.slug).exists():
            if ordered_item.quantity > 1:
                ordered_item.quantity -= 1
                ordered_item.save()
            else:
                order.items.remove(ordered_item)
                ordered_item.delete()
                return redirect("order-summary") 
            messages.info(request,"This item quantity was updated")
        
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(ordered_item)
        messages.info(request,"This item was added  to your cart")
    return redirect("order-summary")
    
def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request,"You do not have a coupon")
        return redirect("checkout")

class AddCouponView(View):
    def post(self, *args, **kwargs):
        if self.request.method == "POST":
            form = CouponForm(self.request.POST or None)
            if form.is_valid():
                try:
                    order = Order.objects.get(user=self.request.user, ordered=False)
                    code = self.request.POST.get('code')
                    order.coupon = get_coupon(self.request, code)
                    order.save()
                    messages.info(self.request,"Succesfully added your coupon")
                    return redirect("checkout")
                except ObjectDoesNotExist:
                    messages.info(self.request,"You do not have an active cart")
                    return redirect("checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            "form":form
        }
        return render(self.request, "request-refund.html", context)
    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get("ref_code")
            message = form.cleaned_data.get("message")
            email = form.cleaned_data.get("email")

            try: 
                order = Order.objects.get(ref_code=ref_code)
                order.refund_request = True
                order.save()

                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your order was received")
                return redirect('request-refund')
            
            except ObjectDoesNotExist:
                messages.warning(self.request, "This order does not excist")
                return redirect('request-refund')
    
    

    