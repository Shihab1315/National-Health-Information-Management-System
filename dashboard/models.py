from django.db import models
from django.utils.text import slugify

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Hero(BaseModel):
    heading = models.CharField(max_length=200)
    subheading = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    button_text = models.CharField(max_length=50)
    button_url = models.URLField(blank=True)
    secondary_button_text = models.CharField(max_length=50, blank=True)
    secondary_button_url = models.URLField(blank=True)
    badge_text = models.CharField(max_length=100, blank=True)
    hero_image = models.ImageField(upload_to='hero/', blank=True, null=True)
    background_image = models.ImageField(upload_to='hero/bg/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Hero Section"
        verbose_name_plural = "Hero Sections"

    def __str__(self):
        return self.heading

class Service(BaseModel):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(max_length=250, help_text="Brief description (1‑2 lines)")
    icon_class = models.CharField(max_length=50, help_text="Font Awesome or Bootstrap icon class, e.g. 'fas fa-notes-medical'")
    icon_color = models.CharField(max_length=20, default='text-blue-400', help_text="Tailwind color class")
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Feature(BaseModel):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=50)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = "Feature"
        verbose_name_plural = "Features"

    def __str__(self):
        return self.title

class Statistic(BaseModel):
    title = models.CharField(max_length=50)
    value = models.CharField(max_length=20)
    icon = models.CharField(max_length=50)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        verbose_name = "Statistic"
        verbose_name_plural = "Statistics"

    def __str__(self):
        return f"{self.value} {self.title}"

class WhyChooseUs(BaseModel):
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Why Choose NHIMS"
        verbose_name_plural = "Why Choose NHIMS"

    def __str__(self):
        return self.title

class Testimonial(BaseModel):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    content = models.TextField()
    image = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    rating = models.PositiveSmallIntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"

    def __str__(self):
        return f"{self.name} - {self.designation}"

class FAQ(BaseModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question

class Partner(BaseModel):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='partners/', blank=True, null=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = "Partner"
        verbose_name_plural = "Partners"

    def __str__(self):
        return self.name

class CTA(BaseModel):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    button_text = models.CharField(max_length=50)
    button_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Call to Action"
        verbose_name_plural = "Call to Action"

    def __str__(self):
        return self.title

class Footer(BaseModel):
    organization_name = models.CharField(max_length=100, default="NHIMS Bangladesh")
    tagline = models.CharField(max_length=200, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    copyright_text = models.CharField(max_length=200, default="© 2026 NHIMS Bangladesh. All rights reserved.")
    quick_links = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "Footer"
        verbose_name_plural = "Footer"

    def __str__(self):
        return self.organization_name