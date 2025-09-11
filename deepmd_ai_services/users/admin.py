from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import User


# admin.site.unregister(User) # has been unregistered in settings.py via  AUTH_USER_MODEL = 'users.User' 
admin.site.unregister(Group)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    # 在列表页显示的字段
    list_display = ('username', 'email', 'user_id', 'auth_provider', 'organization', 'is_active', 'date_joined')
    
    # 可以搜索的字段
    search_fields = ('username', 'email', 'user_id', 'external_id')
    
    # 右侧过滤器
    list_filter = ('auth_provider', 'organization', 'is_active', 'is_staff', 'date_joined')
    
    # 详情页字段布局
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extended Information', {
            'fields': ('user_id', 'auth_provider', 'external_id', 'organization')
        }),
    )
    
    # 添加用户时的字段
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Extended Information', {
            'fields': ('user_id', 'auth_provider', 'external_id', 'organization')
        }),
    )

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass

