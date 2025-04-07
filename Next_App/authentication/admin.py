from datetime import timezone
from django.contrib import admin

from .models import OTP, Booking, BookingExtension, BookingRequest, CustomUser, Partner, Review, ServiceType

# Register your models here.
admin.site.register(CustomUser)

admin.site.register(Partner)

admin.site.register(ServiceType)

admin.site.register(Booking)

admin.site.register(BookingRequest)

admin.site.register(BookingExtension)

admin.site.register(Review)

admin.site.register(OTP)



from django.contrib import admin
from .models import PartnerWallet, Transaction

class PartnerWalletAdmin(admin.ModelAdmin):
    list_display = ('partner', 'balance', 'last_payout_date')
    search_fields = ('partner__full_name', 'partner__phone_number')
    list_filter = ('last_payout_date',)
    
    actions = ['process_payout']
    
    def process_payout(self, request, queryset):
        payout_count = 0
        for wallet in queryset:
            if wallet.balance > 0:
                # Create a transaction record for the payout
                Transaction.objects.create(
                    partner_wallet=wallet,
                    amount=wallet.balance,
                    transaction_type='partner_payout',
                    status='completed'
                )
                
                # Reset wallet balance
                wallet.balance = 0
                wallet.last_payout_date = timezone.now()
                wallet.save()
                payout_count += 1
        
        self.message_user(request, f"Successfully processed payouts for {payout_count} partners.")
    
    process_payout.short_description = "Process payouts for selected partners"

admin.site.register(PartnerWallet, PartnerWalletAdmin)
admin.site.register(Transaction)