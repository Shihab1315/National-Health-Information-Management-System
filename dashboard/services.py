from .models import (
    Hero, Service, Feature, Statistic, WhyChooseUs,
    Testimonial, FAQ, Partner, CTA, Footer
)

class DashboardService:
    @staticmethod
    def get_all_active_data():
        return {
            'hero': Hero.objects.filter(is_active=True).first(),
            'services': Service.objects.filter(is_active=True).order_by('display_order'),
            'features': Feature.objects.filter(is_active=True).order_by('display_order'),
            'stats': Statistic.objects.all().order_by('display_order'),
            'why_choose': WhyChooseUs.objects.all().order_by('order'),
            'testimonials': Testimonial.objects.filter(is_active=True).order_by('-created_at'),
            'faqs': FAQ.objects.filter(is_active=True).order_by('order'),
            'partners': Partner.objects.filter(is_active=True).order_by('display_order'),
            'cta': CTA.objects.filter(is_active=True).first(),
            'footer': Footer.objects.first(),
        }