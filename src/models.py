import datetime
from os.path import dirname, abspath, join
from enum import Enum
from peewee import Model, CharField, IntegerField, SqliteDatabase, \
    ForeignKeyField, DecimalField, BlobField, BooleanField, DateField, DateTimeField, TextField, OperationalError

d = dirname(dirname(abspath(__file__)))
db = SqliteDatabase(join(d, 'db.sqlite'))


class DeliveryMethod(Enum):
    PICKUP = 1
    DELIVERY = 2


class BaseModel(Model):
    class Meta:
        database = db


class Location(BaseModel):
    title = CharField()


class User(BaseModel):
    username = CharField(null=True)
    telegram_id = IntegerField()
    locale = CharField(max_length=4, default='iw')
    phone_number = CharField(null=True)
    # Already set constraint which checks if locale is iw or en
    # def save(self, force_insert=False, only=None):
    #     if self.locale not in (self.HEBREW, self.ENGLISH):
    #         self.locale = self.HEBREW
    #     return super().save(force_insert=force_insert, only=only)


class Courier(User):
    location = ForeignKeyField(Location, null=True)
    is_active = BooleanField(default=True)


class CourierLocation(BaseModel):
    location = ForeignKeyField(Location)
    courier = ForeignKeyField(Courier)


class ProductCategory(BaseModel):
    title = CharField(unique=True)


class Product(BaseModel):
    title = CharField()
    image = BlobField(null=True)
    is_active = BooleanField(default=True)
    credits = IntegerField(default=0)
    category = ForeignKeyField(ProductCategory, related_name='products', null=True)


class ProductMedia(BaseModel):
    product = ForeignKeyField(Product, related_name='product_media')
    file_id = CharField()
    file_type = CharField(null=True)
    #file_path = CharField()
    #type = CharField()


class ProductCount(BaseModel):
    product = ForeignKeyField(Product, related_name='product_counts')
    count = IntegerField()
    price = DecimalField()


class ProductWarehouse(BaseModel):
    # user = ForeignKeyField(User, related_name='user_warehouses', null=True)
    courier = ForeignKeyField(Courier, related_name='courier_warehouses', null=True)
    product = ForeignKeyField(Product, related_name='product_warehouses')
    count = IntegerField(default=0)


class Order(BaseModel):
    user = ForeignKeyField(User, related_name='user_orders')
    courier = ForeignKeyField(Courier, related_name='courier_orders', null=True)
    shipping_method = IntegerField(default=DeliveryMethod.PICKUP.value,
                                   choices=DeliveryMethod)
    shipping_time = DateTimeField(default=datetime.datetime.now)
    location = ForeignKeyField(Location, null=True)
    confirmed = BooleanField(default=False)
    delivered = BooleanField(default=False)
    client_notified = BooleanField(default=False)
    date_created = DateTimeField(default=datetime.datetime.now)


class OrderItem(BaseModel):
    order = ForeignKeyField(Order, related_name='order_items')
    product = ForeignKeyField(Product, related_name='product_items')
    count = IntegerField(default=1)
    total_price = DecimalField(default=0,
                               verbose_name='total price for each item')


class OrderPhotos(BaseModel):
    order = ForeignKeyField(Order, related_name='order_photos')
    photo_id = CharField(null=True)
    stage2_id = CharField(null=True)
    coordinates = CharField(null=True)
    order_hidden_text = TextField()
    order_text = TextField()
    order_text_msg_id = TextField(null=True)


class IdentificationStage(BaseModel):
    # content = CharField()
    active = BooleanField(default=True)
    vip_required = BooleanField(default=False)
    type = CharField()

class IdentificationQuestion(BaseModel):
    content = CharField()
    stage = ForeignKeyField(IdentificationStage, related_name='identification_questions')


class OrderIdentificationAnswer(BaseModel):
    stage = ForeignKeyField(IdentificationStage, related_name='identification_answers')
    question = ForeignKeyField(IdentificationQuestion, related_name='identification_answers')
    order = ForeignKeyField(Order, related_name='identification_answers')
    content = CharField()
    msg_id = CharField(null=True)

def create_tables():
    try:
        db.connect()
    except OperationalError:
        db.close()
        db.connect()

    db.create_tables(
        [
            Location, User, Courier, CourierLocation, ProductCategory, Product, ProductCount,
            Order, OrderItem, OrderPhotos, ProductWarehouse, ProductMedia, IdentificationStage,
            OrderIdentificationAnswer, IdentificationQuestion
        ], safe=True
    )
    # try:
    #     def_cat = ProductCategory.get(title='Default')
    # except ProductCategory.DoesNotExist:
    #     def_cat = ProductCategory.create(title='Default')
    # for product in Product:
    #     if not product.category:
    #         product.category = def_cat
    #         product.save()


def close_db():
    db.close()
