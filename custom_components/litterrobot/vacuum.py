"""Support for Litter-Robot "Vacuum"."""
from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    SUPPORT_SEND_COMMAND,
    SUPPORT_START,
    SUPPORT_STATE,
    SUPPORT_STATUS,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    VacuumEntity,
)
from homeassistant.const import STATE_OFF
from pylitterbot import Robot

from . import LitterRobotEntity
from .const import _LOGGER, LITTERROBOT_DOMAIN

SUPPORT_LITTERROBOT = (
    SUPPORT_START
    | SUPPORT_STATE
    | SUPPORT_STATUS
    | SUPPORT_TURN_OFF
    | SUPPORT_TURN_ON
    | SUPPORT_SEND_COMMAND
)
LITTER_BOX = "Litter Box"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Litter-Robot cleaner using config entry."""
    entities = []
    hub = hass.data[LITTERROBOT_DOMAIN][config_entry.entry_id]

    for robot in hub.account.robots:
        entities.append(LitterRobotCleaner(robot, LITTER_BOX, hub))

    if not entities:
        return

    _LOGGER.debug(f"Adding robot cleaner {entities}")
    async_add_entities(entities, True)


class LitterRobotCleaner(LitterRobotEntity, VacuumEntity):
    """Litter-Robot Cleaner."""

    @property
    def supported_features(self):
        """Flag cleaner robot features that are supported."""
        return SUPPORT_LITTERROBOT

    @property
    def state(self):
        """Return the state of the cleaner."""
        return self.robot.unit_status

    @property
    def error(self):
        """Return the error associated with the current state, if any."""
        return self.robot.unit_status.value

    @property
    def status(self):
        """Return the status of the cleaner."""
        return f"{self.robot.unit_status.value}{' (Sleeping)' if self.robot.is_sleeping else ''}"

    async def async_turn_on(self):
        """Turn the cleaner on, starting a clean cycle."""
        await self.perform_action_and_refresh(self.robot.set_power_status, True)

    async def async_turn_off(self):
        """Turn the unit off, stopping any cleaning in progress as is."""
        await self.perform_action_and_refresh(self.robot.set_power_status, False)

    async def async_start(self):
        """Start a clean cycle."""
        await self.perform_action_and_refresh(self.robot.start_cleaning)

    async def async_send_command(self, command, params=None, **kwargs):
        """Send command.

        Available commands:
          - reset_waste_drawer
            * params: none
          - set_sleep_mode
            * params:
              - enabled: bool
              - sleep_time: str (optional)

        """
        if command == "reset_waste_drawer":
            # Normally we need to request a refresh of data after a command is sent.
            # However, the API for resetting the waste drawer returns a refreshed
            # data set for the robot. Thus, we only need to tell hass to update the
            # state of devices associated with this robot.
            self.robot.reset_waste_drawer()
            self.hub.coordinator.async_set_updated_data(True)
        elif command == "set_sleep_mode":
            await self.perform_action_and_refresh(
                self.robot.set_sleep_mode,
                params.get("enabled"),
                self.parse_time_at_default_timezone(params.get("sleep_time")),
            )
        else:
            raise NotImplementedError()

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return {
            "clean_cycle_wait_time_minutes": self.robot.clean_cycle_wait_time_minutes,
            "is_sleeping": self.robot.is_sleeping,
            "power_status": self.robot.power_status,
            "last_seen": self.robot.last_seen,
        }
