from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('checkout', views.CheckoutView.as_view(), name='checkout'),
    path('product/<slug>', views.DetailView.as_view(), name='product'),
    path('order-summary', views.OrderSummary.as_view(), name='order-summary'),
    path('add_to_card/<slug>', views.add_to_card, name="add-to-card"),
    path('add_coupon/', views.AddCouponView.as_view, name="add-coupon"),
    path('remove_from_card/<slug>', views.remove_from_card, name="remove-from-card"),
    path('remove_single_item_from_card/<slug>', views.remove_single_item_from_card, name="remove-single-item-from-card"),
    path('payment/<payment_option>', views.PaymentView.as_view(), name="payment"),
    path('request-refund', views.RequestRefundView.as_view(), name="request-refund"),
]