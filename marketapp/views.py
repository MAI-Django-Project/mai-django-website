import psycopg2
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import RegForm, Form_buy, Form_change, Add_form, Form_profile
from .models import Products, Markets_prods, Clients_prods, Markets, Clients_orders, Orders_prods
from usersapp.models import Shopper, Profile
from M_Network import settings
from rest_framework.authtoken.models import Token
# Create your views here.
def main_view(request):
    market_prods = []
    prods = []
    title = 'Ассортимент'

    if request.user.is_authenticated:
        assortiment = Markets_prods.objects.select_related('prod_id').filter(market_id=request.user.market_id)
    else:
        assortiment = Products.objects.all()

    paginator = Paginator(assortiment,3)

    page = request.GET.get('page')
    try:
        assortiment = paginator.page(page)
    except PageNotAnInteger:
        assortiment = paginator.page(1)
    except EmptyPage:
        assortiment = paginator.page(paginator.num_pages)
    #for item in assortiment:
        #print(item.)
    return render(request, 'marketapp/index.html', context={'assortiment': assortiment, 'title': title})


def reg(request):
    title = 'Регистрация'
    if request.method == 'POST':
        form = RegForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('market:index'))
        else:
            print('Not valid data')
            return render(request, 'marketapp/signin.html', context={'form': form,'title':title})
    else:
        form = RegForm()
        return render(request, 'marketapp/signin.html', context={'form': form,'title':title})

def product(request,id):
    title = 'Информация'
    product = Products.objects.get(id = id)
    return render(request,'marketapp/product.html',context = {'product_info':product,'title':title})

def product_buy(request,product_id,market_id):
    if request.user.is_staff == False:
        title = 'Покупка'
        product = Products.objects.get(id=product_id)
        if request.method == 'POST':
            form = Form_buy(request.POST)
            if form.is_valid():
                count_duplicates = len(Clients_prods.objects.filter(client_id=request.user.id, product_id=product_id))
                if count_duplicates > 0:
                    print('Нельзя создать две одинаковые позиции')
                    return HttpResponseRedirect(reverse('market:index'))
                count = form.cleaned_data['count']
                Clients_prods.objects.create(pay=0,count=count,client_id=Shopper.objects.get(id=request.user.id),market_id=Markets.objects.get(id=market_id),product_id=Products.objects.get(id=product_id))
                return HttpResponseRedirect(reverse('market:index'))
            else:
                return render(request, 'marketapp/product_buy.html', context={'product_info': product, 'form': form,'title':title})
        else:
            form = Form_buy()
            return render(request,'marketapp/product_buy.html',context = {'product_info':product,'form':form,'title':title})
    else:
        title = 'Редактирование'
        product = Products.objects.get(id=product_id)
        if request.method == 'POST':
            form = Form_change(request.POST)
            if form.is_valid():
                new_count = form.cleaned_data['count']
                if new_count > 0:
                    old_data = Markets_prods.objects.get(prod_id=product_id,market_id=request.user.market_id)
                    old_data.count = new_count
                    old_data.save()
                elif new_count == 0:
                    old_data = Markets_prods.objects.get(prod_id=product_id, market_id=request.user.market_id)
                    old_data.delete()
                return HttpResponseRedirect(reverse('market:index'))
            else:
                return render(request, 'marketapp/product_buy.html', context={'product_info': product, 'form': form,'title':title})
        else:
            form = Form_change()
            return render(request, 'marketapp/product_buy.html', context={'product_info': product, 'form': form,'title':title})

def shopping_cart(request):
    title = 'Корзина'
    products = Clients_prods.objects.select_related('product_id').filter(client_id=request.user.id)
    if request.method=='GET':
        return render(request, 'marketapp/shopping_cart.html', context={'own_cart': products,'title':title})
    else:
        try:
            connection = psycopg2.connect(
                host =settings.db_host,
                user =settings.db_user,
                password =settings.db_pswrd,
                database =settings.db_name,
                port = settings.db_port
            )
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(f'call client_buy_own_shopping_cart_products({request.user.id})')
        except Exception as _ex:
            print('Error while working with PostgreSQL', _ex)
        finally:
            return HttpResponseRedirect(reverse('market:cart'))

@user_passes_test(lambda user: user.profile.delivery_enable,login_url='/profile/')
def by_with_delivery(request):
    try:
        connection = psycopg2.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_pswrd,
            database=settings.db_name,
            port=settings.db_port
        )
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f'call client_buy_own_shopping_cart_products({request.user.id})')
    except Exception as _ex:
        print('Error while working with PostgreSQL', _ex)
    finally:
        return render(request, 'marketapp/buy_delivery.html')


def change_cart(request,product_id):
    title = 'Редактирование'
    product = Products.objects.get(id=product_id)
    cl = Clients_prods.objects.get(client_id=request.user.id, product_id=product_id)
    if request.method == 'POST':
        form = Form_change(request.POST)
        if form.is_valid():
            count = form.cleaned_data['count']

            Clients_prods.change(count,request.user.id,product_id)

            return HttpResponseRedirect(reverse('market:cart'))
        else:
            return render(request, 'marketapp/change.html', context={'product_info': product, 'form': form,'title':title})
    else:
        form = Form_change(request.POST)
        return render(request, 'marketapp/change.html', context={'product_info': product,'count':cl.count, 'form': form,'title':title})

def add_product(request):
    title = 'Добавление'
    if request.method == 'POST':
        form = Add_form(request.POST)
        if form.is_valid():
            prod_id = form.cleaned_data['prod_id']
            count = form.cleaned_data['count']
            try:
                m_prods = Markets_prods.objects.get(market_id=request.user.market_id,prod_id=prod_id)
                if m_prods.id > 0:
                    print('Невозможно добавить дупликат товара')
                    return HttpResponseRedirect(reverse('market:index'))
            except:
                Markets_prods.objects.create(market_id=Markets.objects.get(id=request.user.market_id),prod_id=Products.objects.get(id=prod_id),count=count)
                return HttpResponseRedirect(reverse('market:index'))
        else:
            print('Not valid data')
            return render(request, 'marketapp/add_product.html', context={'form': form,'title':title})
    else:
        form = Add_form()
        return render(request, 'marketapp/add_product.html', context={'form': form,'title':title})

def client_orders(request):
    title = 'Заказы'
    orders = Clients_orders.objects.select_related('client_id').filter(client_id_id = request.user.id)
    prods = Orders_prods.objects.select_related('prod_id','order_id').all()
    for order,i in zip(orders,range(len(orders))):
        order.client_id.id = i+1
    return render(request, 'marketapp/client_orders.html', context={'client_orders': orders,'order_products':prods,'title':title})

def market_orders(request):
    title = 'Заказы'
    orders = Clients_orders.objects.select_related('client_id').all()
    return render(request, 'marketapp/orders_for_manager.html', context={'market_orders': orders,'title':title})

def profile_view(request):
    title = 'Профиль'
    address_info = Profile.objects.get(user_id=request.user.id)
    token = Token.objects.get(user=request.user)
    if request.method=='GET':
        form = Form_profile()
        return render(request, 'marketapp/profile_user.html', context={'title':title,'address':address_info.address,'form':form,'token':token})
    else:
        form = Form_profile(request.POST)
        if form.is_valid():
            new_date = form.cleaned_data['age']
            new_address = form.cleaned_data['address']
            new_phone = form.cleaned_data['phone']
            print(new_date)
            print(new_address)
            print(new_phone)
            request.user.age = new_date
            request.user.phone = new_phone
            address_info.address = new_address
            address_info.delivery_enable = True
            request.user.save()
            address_info.save()
            return HttpResponseRedirect(reverse('market:profile'))
        else:
            print('FORM is invalid')
            return render(request, 'marketapp/profile_user.html', context={'title':title,'address':address_info.address,'form':form,'token':token})

def update_token(requests):
    user = requests.user
    token = Token.objects.get(user = user)
    if token:
        token.delete()
        Token.objects.create(user=user)
    else:
        Token.objects.create(user=user)
    return HttpResponseRedirect(reverse('market:profile'))