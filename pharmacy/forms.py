from django import forms
from django.utils import timezone
from .models import Medicine, Category, Supplier, PurchaseOrder, Sale, InventoryLog
from .validators import validate_positive_stock, validate_expiry_date


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition'
                })
        # Select fields
        for field_name in ['category', 'dosage_form']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white focus:border-blue-500 outline-none transition'
                })

    def clean_current_stock(self):
        stock = self.cleaned_data.get('current_stock')
        if stock is not None and stock < 0:
            raise forms.ValidationError('Stock cannot be negative.')
        return stock

    def clean_expiry_date(self):
        expiry = self.cleaned_data.get('expiry_date')
        validate_expiry_date(expiry)
        return expiry

    # ---- ADDED: Field-specific validation ----
    def clean_selling_price(self):
        selling = self.cleaned_data.get('selling_price')
        if selling is not None and selling < 0:
            raise forms.ValidationError("Selling price cannot be negative.")
        return selling

    def clean_buying_price(self):
        buying = self.cleaned_data.get('buying_price')
        if buying is not None and buying < 0:
            raise forms.ValidationError("Buying price cannot be negative.")
        return buying

    def clean_unit(self):
        unit = self.cleaned_data.get('unit')
        if not unit:
            raise forms.ValidationError("Unit is required.")
        return unit

    def clean_minimum_stock(self):
        min_stock = self.cleaned_data.get('minimum_stock')
        if min_stock is not None and min_stock < 0:
            raise forms.ValidationError("Minimum stock cannot be negative.")
        return min_stock

    def clean_maximum_stock(self):
        max_stock = self.cleaned_data.get('maximum_stock')
        if max_stock is not None and max_stock < 0:
            raise forms.ValidationError("Maximum stock cannot be negative.")
        return max_stock

    # ---- ADDED: Cross-field validation ----
    def clean(self):
        cleaned_data = super().clean()
        buying = cleaned_data.get('buying_price')
        selling = cleaned_data.get('selling_price')
        if buying is not None and selling is not None:
            if selling < buying:
                raise forms.ValidationError("Selling price must be greater than or equal to buying price.")

        stock = cleaned_data.get('current_stock')
        max_stock = cleaned_data.get('maximum_stock')
        if stock is not None and max_stock is not None and stock > max_stock:
            raise forms.ValidationError({"current_stock": "Current stock cannot exceed maximum stock limit."})

        min_stock = cleaned_data.get('minimum_stock')
        max_stock = cleaned_data.get('maximum_stock')
        if min_stock is not None and max_stock is not None and min_stock > max_stock:
            raise forms.ValidationError({"minimum_stock": "Minimum stock cannot be greater than maximum stock."})

        return cleaned_data


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 outline-none transition'
            })

    # ---- ADDED: Field-specific validation ----
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not phone.isdigit() and not phone.replace('+', '').isdigit():
            raise forms.ValidationError("Phone number must contain only digits and optional '+'.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and '@' not in email:
            raise forms.ValidationError("Enter a valid email address.")
        return email


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'purchase_date', 'invoice_number', 'discount', 'vat', 'payment_status', 'remarks']
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 outline-none transition'
                })
        self.fields['supplier'].widget.attrs.update({'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white'})

    # ---- ADDED: Field-specific validation ----
    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount is not None and discount < 0:
            raise forms.ValidationError("Discount cannot be negative.")
        return discount

    def clean_vat(self):
        vat = self.cleaned_data.get('vat')
        if vat is not None and vat < 0:
            raise forms.ValidationError("VAT cannot be negative.")
        return vat


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['patient', 'prescription', 'discount', 'vat', 'payment_method', 'paid_amount', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 outline-none transition'
                })
        self.fields['patient'].widget.attrs.update({'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white'})
        self.fields['prescription'].widget.attrs.update({'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white'})
        self.fields['payment_method'].widget.attrs.update({'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white'})

    # ---- ADDED: Field-specific validation ----
    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount is not None and discount < 0:
            raise forms.ValidationError("Discount cannot be negative.")
        return discount

    def clean_vat(self):
        vat = self.cleaned_data.get('vat')
        if vat is not None and vat < 0:
            raise forms.ValidationError("VAT cannot be negative.")
        return vat

    def clean_paid_amount(self):
        paid = self.cleaned_data.get('paid_amount')
        if paid is not None and paid < 0:
            raise forms.ValidationError("Paid amount cannot be negative.")
        return paid

    # ---- ADDED: Cross-field validation ----
    def clean(self):
        cleaned_data = super().clean()
        patient = cleaned_data.get('patient')
        prescription = cleaned_data.get('prescription')
        if patient and prescription and prescription.patient != patient:
            raise forms.ValidationError("The selected prescription does not belong to the selected patient.")
        return cleaned_data