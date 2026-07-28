from django.contrib import admin
from .models import (
    Hero, Service, Feature, Statistic, WhyChooseUs,
    Testimonial, FAQ, Partner, CTA, Footer
)

@admin.register(Hero)
class HeroAdmin(admin.ModelAdmin):
    list_display = ('heading', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('heading', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Content', {
            'fields': ('heading', 'subheading', 'description', 'badge_text')
        }),
        ('Buttons', {
            'fields': ('button_text', 'button_url', 'secondary_button_text', 'secondary_button_url')
        }),
        ('Images', {
            'fields': ('hero_image', 'background_image')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_order', 'is_featured', 'is_active')
    list_filter = ('is_featured', 'is_active')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('display_order',)

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title',)

@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ('title', 'value', 'display_order')
    ordering = ('display_order',)

@admin.register(WhyChooseUs)
class WhyChooseUsAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')
    ordering = ('order',)

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'rating', 'is_active')
    list_filter = ('is_active', 'rating')
    search_fields = ('name', 'content')

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('question', 'answer')

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'display_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(CTA)
class CTAAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')

@admin.register(Footer)
class FooterAdmin(admin.ModelAdmin):
    list_display = ('organization_name',)

    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)