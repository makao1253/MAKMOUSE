/*
 * hid_io.c
 *
 *  Wspolna obsluga wysylania raportow HID (mysz + klawiatura na jednym
 *  endpoincie IN).
 */

#include "main.h"
#include "usb_device.h"
#include "usbd_hid.h"
#include "hid_io.h"

extern USBD_HandleTypeDef hUsbDeviceFS;

// USBD_HID_SendReport() zwraca USBD_OK, ale po cichu porzuca raport, gdy host
// nie odebral jeszcze poprzedniego - dlatego stan endpointu sprawdzamy przed
// wyslaniem, a nie po. Bez tego raport myszki potrafi zjesc znak klawiatury.
uint8_t hidReadyToSend(void)
{
	USBD_HID_HandleTypeDef *hhid = (USBD_HID_HandleTypeDef*) hUsbDeviceFS.pClassData;

	if(hhid == NULL)
	{
		return 0;
	}

	if(hUsbDeviceFS.dev_state != USBD_STATE_CONFIGURED)
	{
		return 0;
	}

	return (hhid->state == HID_IDLE) ? 1 : 0;
}

uint8_t hidSendReport(uint8_t *report, uint16_t length)
{
	if(!hidReadyToSend())
	{
		return USBD_BUSY;
	}

	return USBD_HID_SendReport(&hUsbDeviceFS, report, length);
}
