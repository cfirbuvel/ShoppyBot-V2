import os
from playhouse.migrate import SqliteDatabase, SqliteMigrator, migrate, ForeignKeyField, CharField
from src.models import db as peewee_db, GroupProductCount, Product

if __name__ == '__main__':
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(d, 'db.sqlite')
    db = SqliteDatabase(db_path)
    peewee_db.connect()
    peewee_db.create_tables([GroupProductCount], safe=True)
    migrator = SqliteMigrator(db)
    group_price_field = ForeignKeyField(GroupProductCount, field=GroupProductCount.id, related_name='products', null=True)
    group_price_field_count = ForeignKeyField(GroupProductCount, field=GroupProductCount.id, related_name='product_counts', null=True)
    migrate(
        migrator.add_column('product', 'group_price_id', group_price_field),
        migrator.add_column('productcount', 'product_group_id', group_price_field_count),
        migrator.drop_not_null('productcount', 'product_id')
    )
    db.close()
    peewee_db.close()

