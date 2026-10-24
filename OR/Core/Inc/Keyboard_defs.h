/*
 * Keyboard_defs.h
 *
 *  Created on: Nov 26, 2024
 *      Author: Piotr Zych
 */

#ifndef INC_KEYBOARD_DEFS_H_
#define INC_KEYBOARD_DEFS_H_
#include "usbd_hid.h"
#include "main.h"
#include "crc.h"
#include "usb_device.h"
#include "gpio.h"

extern USBD_HandleTypeDef hUsbDeviceFS;
#define BUTTON_DELAY		30		// Czas stabilnego stanu wejscia [ms] - odklejanie drgan styku

/*********************************************************************************************************************************/
// Przyciski nie sa juz klawiszami klawiatury - urzadzenie zglasza sie jako
// Multi-axis Controller, wiec kazdy przycisk to jeden bit w bajcie 4 raportu
// HID (Button 1..3). Znaczenie nadaje im aplikacja na PC.
//
// PA2 -> Button 1 (bit 0), PA3 -> Button 2 (bit 1), PA4 -> Button 3 (bit 2)
//
// Piny sa skonfigurowane w MX_GPIO_Init() jako wejscia z pull-up, wiec
// przyciski lacza pin do masy, a stan wcisniety to poziom niski
#define BUTTONS_COUNT		3
#define BUTTONS_ACTIVE_LOW	1

#define BUTTON1_PORT		GPIOA
#define BUTTON1_PIN			GPIO_PIN_2

#define BUTTON2_PORT		GPIOA
#define BUTTON2_PIN			GPIO_PIN_3

#define BUTTON3_PORT		GPIOA
#define BUTTON3_PIN			GPIO_PIN_4

/*********************************************************************************************************************************/
void buttonsInit(void);

// Zwraca bitmaske wcisnietych przyciskow po odklejeniu drgan stykow.
// Wolac w kazdym obiegu petli glownej - funkcja sama probkuje wejscia.
uint8_t buttonsRead(void);
/*********************************************************************************************************************************/
//#define GPIO_PIN_3		22		//B3
//#define GPIO_PIN_4		23		//B4
//#define GPIO_PIN_5		24		//B5
//#define GPIO_PIN_6		11		//B6
//#define GPIO_PIN_7		12		//B7
//#define GPIO_PIN_8		32		//A8
//#define GPIO_PIN_9		33		//A9
//#define GPIO_PIN_10		34		//A10
//#define GPIO_PIN_12		0		//B12
//#define GPIO_PIN_13		13		//B13
//#define GPIO_PIN_14		14		//B14
//#define GPIO_PIN_15		31		//B15
//#define GPIO_PIN_15		21		//A15
/*********************************************************************************************************************************/
/*********************************************************************************************************************************/
// Ponizsze kody HID klawiatury sa NIEUZYWANE w obecnym deskryptorze - zostaja
// jako sciaga, gdyby kiedys wrocila kolekcja klawiatury obok Multi-axis
/*********************************************************************************************************************************/
#define NONE			0x00
#define LEFT_CTRL		0x01
#define LEFT_SHIFT		0x02
#define LEFT_ALT		0x04
#define LEFT_GUI		0x08
#define RIGHT_CTRL		0x10
#define RIGHT_SHIFT		0x20
#define RIGHT_ALT		0x40
#define RIGHT_GUI		0x80

#define RELEASE			0x00
#define SMALL_A			0x04
#define SMALL_B			0x05
#define SMALL_C			0x06
#define SMALL_D			0x07
#define SMALL_E			0x08
#define SMALL_F			0x09
#define SMALL_G			0x0A
#define SMALL_H			0x0B
#define SMALL_I			0x0C
#define SMALL_J			0x0D
#define SMALL_K			0x0E
#define SMALL_L			0x0F
#define SMALL_M			0x10
#define SMALL_N			0x11
#define SMALL_O			0x12
#define SMALL_P			0x13
#define SMALL_Q			0x14
#define SMALL_R			0x15
#define SMALL_S			0x16
#define SMALL_T			0x17
#define SMALL_U			0x18
#define SMALL_V			0x19
#define SMALL_W			0x1A
#define SMALL_X			0x1B
#define SMALL_Y			0x1C
#define SMALL_Z			0x1D

#define KEYBOARD_1		0x1E
#define KEYBOARD_2		0x1F
#define KEYBOARD_3		0x20
#define KEYBOARD_4		0x21
#define KEYBOARD_5		0x22
#define KEYBOARD_6		0x23
#define KEYBOARD_7		0x24
#define KEYBOARD_8		0x25
#define KEYBOARD_9		0x26
#define KEYBOARD_0		0x27

#define ENTER			0x28
#define ESCAPE			0x29
#define BACKSPACE		0x2A
#define TAB				0x2B
#define SPACEBAR		0x2C

#define KEYBOARD_F1		0x3A
#define KEYBOARD_F2		0x3B
#define KEYBOARD_F3		0x3C
#define KEYBOARD_F4		0x3D
#define KEYBOARD_F5		0x3E
#define KEYBOARD_F6		0x3F
#define KEYBOARD_F7		0x40
#define KEYBOARD_F8		0x41
#define KEYBOARD_F9		0x42
#define KEYBOARD_F10	0x43
#define KEYBOARD_F11	0x44
#define KEYBOARD_F12	0x45

// UWAGA: F13 nie jest kolejna wartoscia po F12 (0x45) - klawisze F13-F24 leza
// wyzej, od 0x68. Kody powyzej Usage Maximum w deskryptorze (0x73) host ignoruje
#define KEYBOARD_F13	0x68
#define KEYBOARD_F14	0x69
#define KEYBOARD_F15	0x6A
#define KEYBOARD_F16	0x6B
#define KEYBOARD_F17	0x6C
#define KEYBOARD_F18	0x6D
#define KEYBOARD_F19	0x6E
#define KEYBOARD_F20	0x6F
#define KEYBOARD_F21	0x70
#define KEYBOARD_F22	0x71
#define KEYBOARD_F23	0x72
#define KEYBOARD_F24	0x73
#endif /* INC_KEYBOARD_DEFS_H_ */
