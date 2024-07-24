from enum import IntEnum

from tortoise import Model, fields


class UpdateModeEnum(IntEnum):
    LATEST = 1
    PINNED = 2
    ROLLOUT = 3
    ASSIGNED = 4

    def __str__(self):
        if self == UpdateModeEnum.LATEST:
            return "Latest"
        elif self == UpdateModeEnum.PINNED:
            return "Pinned"
        elif self == UpdateModeEnum.ROLLOUT:
            return "Rollout"
        elif self == UpdateModeEnum.ASSIGNED:
            return "Assigned"


class Tag(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)


class Device(Model):
    uuid = fields.CharField(max_length=255, primary_key=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    name = fields.CharField(max_length=255, null=True)
    hw_model = fields.CharField(max_length=255, null=True, default="default")
    hw_revision = fields.CharField(max_length=255, null=True, default="default")
    feed = fields.CharField(max_length=255, default="default")
    flavor = fields.CharField(max_length=255, default="default")
    update_mode = fields.IntEnumField(UpdateModeEnum, default=UpdateModeEnum.ROLLOUT)
    assigned_firmware = fields.ForeignKeyField(
        "models.Firmware", related_name="assigned_devices", null=True
    )
    installed_firmware = fields.ForeignKeyField(
        "models.Firmware", related_name="installed_devices", null=True
    )
    last_state = fields.CharField(max_length=255, null=True, default="unknown")
    progress = fields.IntField(null=True)
    last_log = fields.TextField(null=True)
    last_seen = fields.BigIntField(null=True)
    last_ip = fields.CharField(max_length=15, null=True)
    last_ipv6 = fields.CharField(max_length=40, null=True)
    tags = fields.ManyToManyField(
        "models.Tag", related_name="devices", through="device_tags"
    )


class Firmware(Model):
    id = fields.IntField(primary_key=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    name = fields.CharField(max_length=255, null=True)
    hw_model = fields.CharField(max_length=255, null=True, default="default")
    hw_revision = fields.CharField(max_length=255, null=True, default="default")
    flavor = fields.CharField(max_length=255, default="default")
    version = fields.CharField(max_length=255)
    sha1 = fields.CharField(max_length=40)
    size = fields.IntField(max_length=40)
    file = fields.CharField(max_length=255)


class Rollout(Model):
    id = fields.IntField(primary_key=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    name = fields.CharField(max_length=255, null=True)
    feed = fields.CharField(max_length=255, default="default")
    flavor = fields.CharField(max_length=255, default="default")
    firmware = fields.ForeignKeyField("models.Firmware", related_name="rollouts")
    paused = fields.BooleanField(default=False)
    success_count = fields.IntField(default=0)
    failure_count = fields.IntField(default=0)
