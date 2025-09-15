import asyncio
import os
import sys
import getpass
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

# --- Path Setup ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

# --- وارد کردن مدل‌های صحیح و تنظیمات ---
# مطمئن شوید مدل Role شما اصلاح شده است (همانطور که در پاسخ قبلی گفتم)
from app.domain.entities_refactored import Admin, Role, PermissionDetail 
from app.core.config import settings
from app.core.security import get_password_hash

async def create_admin():
    """
    اسکریپت تعاملی برای ساخت ادمین با نقش‌های استاندارد.
    """
    print("--- ابزار ساخت کاربر ادمین ---")

    client = AsyncIOMotorClient(settings.database_url)
    db_name = client.get_default_database().name
    await init_beanie(database=client[db_name], document_models=[Admin, Role])
    print("اتصال به دیتابیس موفقیت‌آمیز بود.")

    try:
        email = input("ایمیل ادمین را وارد کنید: ").strip()
        full_name = input("نام کامل ادمین را وارد کنید: ").strip()
        
        # از کاربر بخواهید از نقش‌های استاندارد استفاده کند
        role_name_input = input("نقش مورد نظر را وارد کنید (SuperAdmin یا Admin): ").strip()
        
        # بررسی می‌کنیم که نقش وارد شده معتبر باشد
        if role_name_input not in ["SuperAdmin", "Admin"]:
            print("\n[خطا] نقش نامعتبر است. لطفاً از 'SuperAdmin' یا 'Admin' استفاده کنید.")
            return

        password = getpass.getpass("رمز عبور را وارد کنید: ").strip()
        confirm_password = getpass.getpass("رمز عبور را تایید کنید: ").strip()

        # ... (بقیه اعتبارسنجی‌های ورودی) ...

    except KeyboardInterrupt:
        print("\nعملیات توسط کاربر لغو شد.")
        return

    # پیدا کردن نقش در دیتابیس
    target_role = await Role.find_one(Role.name == role_name_input)
    if not target_role:
        print(f"\n[خطا] نقش '{role_name_input}' در دیتابیس یافت نشد. آیا سرور حداقل یک بار اجرا شده است؟")
        return

    # بررسی وجود ادمین تکراری
    if await Admin.find_one(Admin.email == email):
        print(f"\n[خطا] ادمین با ایمیل '{email}' از قبل وجود دارد.")
        return

    # ساخت ادمین جدید
    new_admin = Admin(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        role_id=str(target_role.id),
        role_name=target_role.name,
        is_active=True
    )
    await new_admin.insert()
    print(f"\n✅ ادمین '{full_name}' با نقش '{role_name_input}' با موفقیت ایجاد شد!")


if __name__ == "__main__":
    # مطمئن شوید مدل Role شما در فایل entities_refactored.py اصلاح شده باشد
    # در غیر این صورت این اسکریپت هم همان خطای قبلی را خواهد داد
    asyncio.run(create_admin())