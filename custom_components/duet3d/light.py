import logging
import colorsys
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DuetDataUpdateCoordinator
from .const import (
    ATTR_GCODE,
    CONF_LIGHT,
    CONF_STANDALONE,
    DOMAIN,
    SERVICE_SEND_GCODE,
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Duet3D light platform."""
    if config_entry.data.get(CONF_STANDALONE):
        return

    if config_entry.data.get(CONF_LIGHT):
        coordinator: DuetDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
        device_id = config_entry.entry_id
        assert device_id is not None
        async_add_entities([Duet3DLight(coordinator, "LED", device_id)])


class Duet3DLight(CoordinatorEntity[DuetDataUpdateCoordinator], LightEntity):
    """Representation of a light connected to a Duet3D printer."""
    def __init__(self, coordinator, name, device_id):
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_light_{name}"
        self._attr_has_entity_name = True
        self._attr_should_poll = False
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._attr_color_mode = ColorMode.RGB
        self._state = False
        self._brightness = 255
        self._rgb_color = (255, 255, 255)
        self._last_brightness = self._brightness

    @property
    def device_info(self):
        """Device info."""
        return self.coordinator.device_info

    @property
    def is_on(self):
        """Return the state of the light."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the RGB color of the light."""
        return self._rgb_color

    def _hs_to_rgb(self, hs_color):
        rgb_color = colorsys.hsv_to_rgb(hs_color[0] / 360, hs_color[1] / 100, 1)
        return tuple(int(round(x * 255)) for x in rgb_color)

    async def async_turn_on(self, **kwargs):
        self._state = True

        # Set the brightness if it was passed in the service call
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            self._last_brightness = self._brightness
        else:
            # Use the last brightness value if it was not passed in the service call
            self._brightness = self._last_brightness

        # Set the RGB color if it was passed in the service call
        if ATTR_HS_COLOR in kwargs:
            self._rgb_color = self._hs_to_rgb(kwargs[ATTR_HS_COLOR])

        # Build the M150 GCode command
        command = "M150 R{} U{} B{} P{}".format(
            self._rgb_color[0], self._rgb_color[1], self._rgb_color[2], self._brightness
        )

        # Call the send_code service to send the M150 GCode to the Duet3D board
        await self._send_command_to_printer(command)

        # Update the light state in Home Assistant
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        self._state = False
        # Save the last set brightness before turning the light off
        self._last_brightness = self._brightness
        self._brightness = 0

        # Build the M150 GCode command to turn the light off
        command = "M150 R0 U0 B0 P0"

        # Call the send_code service to send the M150 GCode to the Duet3D board
        await self._send_command_to_printer(command)

        # Update the light state in Home Assistant
        self.async_write_ha_state()

    async def _send_command_to_printer(self, command):
        """Internal method to call the G-code service."""
        try:
            await self.hass.services.async_call(
                DOMAIN,
                SERVICE_SEND_GCODE,
                {ATTR_GCODE: command},
                blocking=True # Esperamos a que se envíe
            )
        except Exception as e:
            _LOGGER.error("Error al enviar G-code a Duet3D: %s", e)
