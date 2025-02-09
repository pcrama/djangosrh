from typing import Self

from django.db import models

class Payment(models.Model):
    date_received = models.DateField(null=False) # When payment was received by the bank
    amount_in_cents = models.IntegerField(null=False)
    comment = models.CharField(max_length=512, blank=True)
    src_id = models.CharField(max_length=32, blank=True)
    bank_ref= models.CharField(max_length=32, blank=False, null=False)
    other_account= models.CharField(max_length=40, blank=True)
    other_name= models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=16, blank=False)
    active = models.BooleanField(db_default=True)
    srh_bank_id = models.CharField(max_length=12, blank=True, null=False)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["src_id"]),
            models.Index(fields=["bank_ref"]),
            models.Index(fields=["srh_bank_id"])
        ]
        constraints = [models.UniqueConstraint(fields=["bank_ref"], name="unique_bank_ref")]

    def __str__(self):
        return f"{self.bank_ref}:{self.amount_in_cents}c€"

    @classmethod
    def find_by_bank_ref(cls, bank_ref: str) -> Self | None:
        try:
            return cls.objects.get(bank_ref=bank_ref)
        except cls.DoesNotExist:
            return None
