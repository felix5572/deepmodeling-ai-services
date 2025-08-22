from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json
from .models import Queuejob, QueuejobStatus


@admin.register(Queuejob)
class QueuejobAdmin(admin.ModelAdmin):
    """
    Admin interface for Queuejob model
    """
    
    # List display
    list_display = [
        'queuejob_id',
        'queuejob_name',
        'user_id_display',
        'status_badge',
        'modal_info',
        'created_at',
        'updated_at'
    ]
    
    # List filters
    list_filter = [
        'current_status',
        'modal_app_name',
        'modal_function_name',
        'created_at',
        'updated_at'
    ]
    
    # Search fields
    search_fields = [
        'queuejob_id',
        'queuejob_name',
        'user_id',
        'user_email',
        'queuejob_hash',
        'modal_function_call_id'
    ]
    
    # Readonly fields
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'status_history_display'
    ]
    
    # Field organization
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'queuejob_id',
                'queuejob_name',
                'queuejob_hash'
            )
        }),
        ('User Information', {
            'fields': (
                'user_id',
                'user_email'
            )
        }),
        ('Modal Platform', {
            'fields': (
                'modal_function_call_id',
                'modal_app_name',
                'modal_function_name'
            ),
            'classes': ('collapse',)
        }),
        ('Execution', {
            'fields': (
                'command',
                'environment_vars'
            ),
            'classes': ('collapse',)
        }),
        ('Status & History', {
            'fields': (
                'current_status',
                'status_history_display'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    # Ordering
    ordering = ['-created_at']
    
    # List per page
    list_per_page = 50
    
    # Actions
    actions = ['mark_as_cancelled', 'mark_as_failed']
    
    def user_id_display(self, obj):
        """Display user_id with prefix highlighting"""
        if not obj.user_id:
            return '-'
        
        if ':' in obj.user_id:
            prefix, identifier = obj.user_id.split(':', 1)
            return format_html(
                '<span style="background: #e3f2fd; padding: 2px 4px; border-radius: 3px; font-size: 0.9em;">{}</span>:{}',
                prefix,
                identifier[:20] + ('...' if len(identifier) > 20 else '')
            )
        return obj.user_id[:30] + ('...' if len(obj.user_id) > 30 else '')
    
    user_id_display.short_description = 'User'
    user_id_display.admin_order_field = 'user_id'
    
    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            QueuejobStatus.SUBMITTED: '#6c757d',
            QueuejobStatus.PENDING: '#ffc107',
            QueuejobStatus.RUNNING: '#17a2b8',
            QueuejobStatus.COMPLETED: '#28a745',
            QueuejobStatus.FAILED: '#dc3545',
            QueuejobStatus.CANCELLED: '#6c757d',
            QueuejobStatus.CLEANED: '#6f42c1',
            QueuejobStatus.TIMEOUT: '#fd7e14'
        }
        
        color = colors.get(obj.current_status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold;">{}</span>',
            color,
            obj.get_current_status_display()
        )
    
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'current_status'
    
    def modal_info(self, obj):
        """Display Modal app and function info"""
        if obj.modal_app_name or obj.modal_function_name:
            app = obj.modal_app_name or '?'
            func = obj.modal_function_name or '?'
            return format_html(
                '<code style="font-size: 0.9em;">{}<br/>└─ {}</code>',
                app,
                func
            )
        return '-'
    
    modal_info.short_description = 'Modal App/Function'
    
    def status_history_display(self, obj):
        """Display formatted status history"""
        if not obj.status_history:
            return "No status history"
        
        html_parts = []
        for event in obj.status_history[-10:]:  # Show last 10 events
            try:
                status = event.get('data', {}).get('status', 'Unknown')
                message = event.get('data', {}).get('message', '')
                timestamp = event.get('time', '')
                
                # Parse timestamp for display
                if timestamp:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%m-%d %H:%M:%S')
                    except:
                        time_str = timestamp[:16]
                else:
                    time_str = 'Unknown time'
                
                html_parts.append(format_html(
                    '<div style="margin: 2px 0; padding: 4px; background: #f8f9fa; border-left: 3px solid #007bff;">'
                    '<strong>{}</strong> <span style="color: #6c757d; font-size: 0.9em;">{}</span><br/>'
                    '<span style="font-size: 0.85em;">{}</span>'
                    '</div>',
                    status,
                    time_str,
                    message if message else 'No message'
                ))
            except Exception as e:
                html_parts.append(f'<div>Error parsing event: {str(e)}</div>')
        
        if len(obj.status_history) > 5:
            html_parts.insert(0, f'<div style="color: #6c757d; font-style: italic;">Showing last 5 of {len(obj.status_history)} events</div>')
        
        return mark_safe(''.join(html_parts))
    
    status_history_display.short_description = 'Recent Status History'
    
    def mark_as_cancelled(self, request, queryset):
        """Admin action to cancel selected jobs"""
        count = 0
        for job in queryset:
            if job.current_status in [QueuejobStatus.SUBMITTED, QueuejobStatus.PENDING, QueuejobStatus.RUNNING]:
                job.add_status(QueuejobStatus.CANCELLED, "Cancelled by admin")
                count += 1
        
        self.message_user(request, f'{count} jobs marked as cancelled.')
    
    mark_as_cancelled.short_description = "Cancel selected jobs"
    
    def mark_as_failed(self, request, queryset):
        """Admin action to mark selected jobs as failed"""
        count = 0
        for job in queryset:
            if not job.is_completed:
                job.add_status(QueuejobStatus.FAILED, "Marked as failed by admin")
                count += 1
        
        self.message_user(request, f'{count} jobs marked as failed.')
    
    mark_as_failed.short_description = "Mark selected jobs as failed"
