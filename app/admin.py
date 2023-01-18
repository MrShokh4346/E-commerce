from django.contrib import admin
from .models import Order, OrderItem, Item, Address, Payment, Coupon, Refund

# Register your models here.

def make_refund_accepted(modeladmiin, request, queryset):
    queryset.update(refund_request=False, refund_granted=True)


make_refund_accepted.short_description = 'Update orders to refund granted'


class OrderAdmin(admin.ModelAdmin):
    list_display = ['user',
                    'ordered',
                    'being_delivered',
                    'receving',
                    'refund_request',
                    'refund_granted',
                    'shipping_address',
                    'billing_address',
                    'payment',
                    'coupon',
                    ]
    list_display_links = [
                    'user',
                    'shipping_address',
                    'billing_address',
                    'payment',
                    'coupon',
    ]
    list_filter = [
                    'ordered',
                    'being_delivered',
                    'receving',
                    'refund_request',
                    'refund_granted'
                    ]
    search_fields = [
        'user__username',
        'ref_code'
    ]
    actions = [make_refund_accepted]

class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'street_address',
        'appatrment_address',
        'country',
        'zip',
        'address_type',
        'default'
    ]
    list_filter = ['default', 'address_type', 'country']
    search_fields = ['user', 'street_address', 'appatrment_address', 'zip']


admin.site.register(Item)
admin.site.register(Coupon)
admin.site.register(OrderItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(Payment)
admin.site.register(Refund)
admin.site.register(Address, AddressAdmin)