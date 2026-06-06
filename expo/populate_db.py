from public.models import Country, City, Exhibition
from django.contrib.auth.models import User
from datetime import date, timedelta

# Create a user if none exists
user, _ = User.objects.get_or_create(username='admin', is_staff=True, is_superuser=True)
user.set_password('admin')
user.save()

# Countries
usa, _ = Country.objects.get_or_create(name='USA')
uk, _ = Country.objects.get_or_create(name='UK')
india, _ = Country.objects.get_or_create(name='India')

# Cities
ny, _ = City.objects.get_or_create(name='New York', country=usa)
la, _ = City.objects.get_or_create(name='Los Angeles', country=usa)
lon, _ = City.objects.get_or_create(name='London', country=uk)
bom, _ = City.objects.get_or_create(name='Mumbai', country=india)

# Exhibitions
Exhibition.objects.get_or_create(
    title='Tech Expo 2026',
    description='A great tech expo',
    category='Technology',
    country=usa,
    city=ny,
    start_date=date.today(),
    end_date=date.today() + timedelta(days=5),
    status='approved',
    user=user
)

Exhibition.objects.get_or_create(
    title='Art Fair',
    description='Beautiful art',
    category='Art',
    country=india,
    city=bom,
    start_date=date.today() - timedelta(days=10),
    end_date=date.today() - timedelta(days=5),
    status='approved',
    user=user
)

print('Sample data created.')
