/*
 * hid_io.h
 *
 *  Wspolna obsluga wysylania raportow HID. Mysz i klawiatura dziela jeden
 *  endpoint IN, wiec obie musza pytac o to samo: czy host odebral juz
 *  poprzedni raport.
 */

#ifndef INC_HID_IO_H_
#define INC_HID_IO_H_

#include "main.h"

// 1 = endpoint wolny, mozna wyslac raport
uint8_t hidReadyToSend(void);

// Wysyla raport tylko wtedy, gdy endpoint jest wolny.
// Zwraca USBD_OK wylacznie po faktycznym wyslaniu, w przeciwnym razie USBD_BUSY.
uint8_t hidSendReport(uint8_t *report, uint16_t length);

#endif /* INC_HID_IO_H_ */
