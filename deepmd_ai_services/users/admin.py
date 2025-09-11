from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # 在列表页显示的字段
    list_display = ('username', 'email', 'user_id', 'auth_provider', 'organization', 'is_active', 'date_joined')
    
    # 可以搜索的字段
    search_fields = ('username', 'email', 'user_id', 'external_id')
    
    # 右侧过滤器
    list_filter = ('auth_provider', 'organization', 'is_active', 'is_staff', 'date_joined')
    
    # 详情页字段布局
    fieldsets = UserAdmin.fieldsets + (
        ('Extended Information', {
            'fields': ('user_id', 'auth_provider', 'external_id', 'organization')
        }),
    )
    
    # 添加用户时的字段
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extended Information', {
            'fields': ('user_id', 'auth_provider', 'external_id', 'organization')
        }),
    )

admin.site.register(User, CustomUserAdmin)