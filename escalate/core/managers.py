from django.contrib.auth.base_user import BaseUserManager

# from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models import Q


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, username, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, password, **extra_fields)


class ExperimentTemplateManager(models.Manager):
    def get_queryset(self):
        return (
            super(ExperimentTemplateManager, self)
            .get_queryset()
            .filter(parent__isnull=True)
        )

    def create(self, **kwargs):
        # kwargs.update({'type': 'video'})
        kwargs.update({"parent": None})
        return super(ExperimentTemplateManager, self).create(**kwargs)


class ExperimentInstanceManager(models.Manager):
    def get_queryset(self):
        return (
            super(ExperimentInstanceManager, self)
            .get_queryset()
            .filter(parent__isnull=False)
        )

    def create(self, **kwargs):
        return super(ExperimentInstanceManager, self).create(**kwargs)


class ExperimentCompletedInstanceManager(models.Manager):
    def get_queryset(self):
        return (
            super(ExperimentCompletedInstanceManager, self)
            .get_queryset()
            .filter(completion_status="Completed")
        )

    def create(self, **kwargs):
        return super(ExperimentCompletedInstanceManager, self).create(**kwargs)


class ExperimentPendingInstanceManager(models.Manager):
    def get_queryset(self):
        return (
            super(ExperimentPendingInstanceManager, self)
            .get_queryset()
            .filter(~Q(completion_status="Completed"))
            .filter(~Q(completion_status="Invalid"))
        )

    def create(self, **kwargs):
        return super(ExperimentPendingInstanceManager, self).create(**kwargs)


class BomMaterialManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                vessel__isnull=True,
                inventory_material__isnull=False,
                #mixture__isnull=True,
            )
        )

    def create(self, **kwargs):
        #kwargs.update({"mixture": None})
        return super().create(**kwargs)


class BomCompositeMaterialManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                vessel__isnull=True,
                inventory_material__isnull=True,
                #mixture__isnull=False,
            )
        )

    def create(self, **kwargs):
        kwargs.update({"inventory_material": None})
        return super().create(**kwargs)


class BomVesselManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                vessel__isnull=False,
                #mixture__isnull=True,
                inventory_material__isnull=True,
            )
        )

    def create(self, **kwargs):
        # kwargs.update({'vessel': None})
        return super().create(**kwargs)


class OutcomeValueManager(models.Manager):
    """Stores the nominal and actual values related to an outcome instance

    Args:
        models ([type]): [description]
    """

    def get_queryset(self):
        return super().get_queryset().filter(outcome_instance__isnull=False)

    def create(self, **kwargs):
        return super().create(**kwargs)
