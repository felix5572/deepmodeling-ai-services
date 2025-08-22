from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class QueuejobStatus(models.TextChoices):
    """Queue Job status enumeration"""
    SUBMITTED = 'SUBMITTED', 'Submitted'
    PENDING = 'PENDING', 'Pending'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    CLEANED = 'CLEANED', 'Cleaned'
    TIMEOUT = 'TIMEOUT', 'Timeout'


class QueuejobStatusEvent(BaseModel):
    """
    Queuejob status change event following CloudEvent specification
    https://cloudevents.io/
    """
    # CloudEvent required fields
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier"
    )
    source: str = Field(
        default="deepmd.ai/batch-queue",
        description="Event source identifier"
    )
    specversion: str = Field(
        default="1.0",
        description="CloudEvent specification version"
    )
    type: str = Field(
        default="deepmd.modal.batch.queuejob.status.changed",
        description="Event type identifier"
    )
    time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp"
    )
    
    # CloudEvent optional fields
    subject: Optional[str] = Field(
        default=None,
        description="Subject of the event (queuejob_id)"
    )
    datacontenttype: str = Field(
        default="application/json",
        description="Content type of data"
    )
    
    # Event data (queuejob status specific)
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload data"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def create_status_change_event(
        cls,
        queuejob_id: str,
        new_status: str,
        subject: str = "django_internal_service",
        message: str = "",
    ) -> "QueuejobStatusEvent":
        """Create a standardized queuejob status change event"""
        return cls(
            subject=subject,
            data={
                "queuejob_id": queuejob_id,
                "status": new_status,
                "message": message,
            }
        )


class Queuejob(models.Model):
    """
    Batch processing queuejob model for Modal integration
    """
    # Primary key
    id = models.AutoField(
        primary_key=True,
        help_text="Database primary key"
    )
    
    # Basic information
    queuejob_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Business unique queuejob identifier"
    )
    
    queuejob_name = models.CharField(
        max_length=100,
        blank=True,
        default="Untitled Queuejob",
        help_text="Human readable queuejob name"
    )

    queuejob_hash = models.CharField(
        max_length=100,
        blank=True,
        help_text="Hash of the queuejob command,files,etc. regrad as the same job's resubmit if the hash is the same."
    )
    
    # User information (flexible for multiple auth systems)
    user_id = models.CharField(
        blank=True,
        max_length=200,
        help_text="User identifier django_myusername123; supabase_otherusername456; etc."
    )

    user_email = models.EmailField(
        blank=True,
        help_text="User email for notifications"
    )
    
    # Modal platform information

    modal_function_call_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Modal function call ID"
    )

    modal_app_name = models.CharField(
        blank=True,
        max_length=100,
        help_text="Modal app name"
    )

    modal_function_name = models.CharField(
        blank=True,
        max_length=100,
        help_text="Modal function name"
    )

    modal_volume_name = models.CharField(
        blank=True,
        max_length=100,
        help_text="Modal volume name"
    )
    
    # Execution configuration
    command = models.TextField(
        blank=True,
        help_text="Command or parameters to execute"
    )
    environment_vars = models.JSONField(
        default=dict,
        blank=True,
        help_text="Environment variables as JSON"
    )
    
    # Status tracking
    status_history = models.JSONField(
        default=list,
        blank=True,
        help_text="Status change history as JSON array"
    )

    current_status = models.CharField(
        blank=True,
        max_length=20,
        choices=QueuejobStatus.choices,
        default=QueuejobStatus.SUBMITTED,
        help_text="Current queuejob status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Queuejob creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'current_status']),
            models.Index(fields=['current_status', '-created_at']),
            models.Index(fields=['modal_app_name', 'modal_function_name']),
        ]
    
    def __str__(self):
        return f"{self.job_name} ({self.job_id}) - {self.current_status}"
    
    def add_status(self, status, message=""):
        """
        Add new status to history and update current status
        """
        # Create CloudEvent-compliant event
        event = QueuejobStatusEvent.create_status_change_event(
            queuejob_id=self.queuejob_id,
            new_status=status,
            message=message,
        )
        
        # Store CloudEvent in history
        self.status_history.append(event.model_dump())
        self.current_status = status
        self.save()
        
        return event
    

    
    @property
    def is_running(self):
        """Check if queuejob is currently running"""
        return self.current_status == QueuejobStatus.RUNNING
    
    @property
    def is_completed(self):
        """Check if queuejob is completed (success or failure)"""
        return self.current_status in [
            QueuejobStatus.COMPLETED,
            QueuejobStatus.FAILED,
            QueuejobStatus.CANCELLED,
            QueuejobStatus.TIMEOUT,
            QueuejobStatus.CLEANED
        ]
