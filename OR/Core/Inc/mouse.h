/*
 * mouse.h
 *
 *  Created on: Sep 3, 2025
 *      Author: Piotr
 *
 *  Raporty HID urzadzenia Multi-axis Controller (mysz 3D). Urzadzenie nie jest
 *  ani mysza, ani klawiatura - surowe raporty odbiera i interpretuje aplikacja
 *  na PC.
 */

#ifndef INC_MOUSE_H_
#define INC_MOUSE_H_

#include "main.h"

/************************************ JOYSTICK ***********************************/
#define JOYSTICK_MIN 0
#define JOYSTICK_MAX 4095
#define JOYSTICK_CENTER 2048
#define DEADZONE 150 // Martwa strefa wokół środka

// Konfiguracja czułości
#define SENSITIVITY 8 // Maksymalne wychylenie osi na jeden raport HID

// Odstęp między raportami HID [ms] - wyznacza tempo narastania osi
#define MOUSE_REPORT_INTERVAL_MS 10

// Rozdzielczość podpikselowa - umożliwia przyrost mniejszy niż 1 na raport
#define MOUSE_SUBPIXEL 256

/************************************ ENKODER ************************************/
// Ile impulsów enkodera daje jeden krok osi Rz (zwiększ, gdy krok za drobny -
// przy TIM_ENCODERMODE_TI1 typowy enkoder daje 2 impulsy na jeden zaskok)
#define ENCODER_COUNTS_PER_STEP 1

#if ENCODER_COUNTS_PER_STEP < 1
#error "ENCODER_COUNTS_PER_STEP musi byc >= 1"
#endif

// Ustaw na 1, aby odwrócić kierunek osi Rz
#define ENCODER_INVERT 0

/************************************ RAPORT HID *********************************/
// Numer raportu - musi sie zgadzac z Report ID (1) w deskryptorze raportow
// (HID_MOUSE_ReportDesc w usbd_hid.c)
#define MULTIAXIS_REPORT_ID 0x01

// Raport: [0] Report ID, [1] X, [2] Y, [3] Rz, [4] przyciski
#define MULTIAXIS_REPORT_SIZE 5

// Maski przycisków w bajcie 4 raportu - Button 1..3 z deskryptora
typedef enum {
    NO_BUTTON = 0x00,
    BUTTON_1 = 0x01,
    BUTTON_2 = 0x02,
    BUTTON_3 = 0x04
} MultiAxisButton_e;

#define BUTTONS_MASK (BUTTON_1 | BUTTON_2 | BUTTON_3)

/*********************************************************************************/
void mouseInit(void);
uint8_t sendAxisReport(int8_t x, int8_t y, int8_t rz, uint8_t buttons);

// Jeden raport HID z przyrostem obu osi joysticka, krokiem enkodera i stanem
// przyciskow naraz. Wolac w kazdym obiegu petli glownej - funkcja sama pilnuje
// tempa raportow.
void processMouseInput(uint8_t buttons);

#endif /* INC_MOUSE_H_ */
