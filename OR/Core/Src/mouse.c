/*
 * mouse.c
 *
 *  Created on: Sep 3, 2025
 *      Author: Piotr
 *
 *  Sklada i wysyla raporty HID Multi-axis Controller: przyrost obu osi
 *  joysticka, krok enkodera na osi Rz oraz stan przyciskow.
 */

#include "main.h"
#include "usb_device.h"
#include "usbd_hid.h"
#include "tim.h"
#include "hid_io.h"
#include "mouse.h"

extern volatile uint32_t axisX, axisY, encoder;

// Stan licznika enkodera z ostatniego odczytu
static uint32_t lastEncoderValue;

// Przyrosty, które jeszcze nie zmieściły się w wysłanych raportach
static int32_t pendingX;
static int32_t pendingY;
static int32_t pendingRz;

// Stan przycisków z ostatniego wysłanego raportu
static uint8_t lastButtons;

// Znacznik czasu ostatniego raportu
static uint32_t lastReportTick;

static int32_t clampToRange(int32_t value, int32_t limit)
{
	if(value > limit)
	{
		return limit;
	}

	if(value < -limit)
	{
		return -limit;
	}

	return value;
}

static int8_t clampToInt8(int32_t value)
{
	return (int8_t) clampToRange(value, 127);
}

// Wychylenie osi w jednostkach podpikselowych (MOUSE_SUBPIXEL jednostek = 1).
// Liczone ze znakiem - na uint32_t odchylenie w lewo/dół dawało ogromną
// liczbę dodatnią i przypadkowy kierunek.
static int32_t axisToSubpixelMovement(uint32_t rawValue)
{
	int32_t offset = (int32_t) rawValue - (int32_t) JOYSTICK_CENTER;

	if(offset > DEADZONE)
	{
		offset -= DEADZONE;
	}
	else if(offset < -DEADZONE)
	{
		offset += DEADZONE;
	}
	else
	{
		return 0; // martwa strefa wokół środka
	}

	return (offset * SENSITIVITY * MOUSE_SUBPIXEL) / (int32_t) (JOYSTICK_CENTER - DEADZONE);
}

// Liczba impulsów enkodera od ostatniego odczytu, z obsługą przekręcenia
// licznika (TIM2 ma ARR = 19, więc zawija się co kilkanaście impulsów).
static int32_t readEncoderCounts(void)
{
	uint32_t period = __HAL_TIM_GET_AUTORELOAD(&htim2) + 1U;
	uint32_t current = __HAL_TIM_GET_COUNTER(&htim2);
	int32_t delta;

	encoder = current;

	// Odejmowanie na uint32_t liczy różnicę modulo 2^32
	delta = (int32_t) (current - lastEncoderValue);

	// Przy krótszym liczniku (tu ARR = 19) sprowadzamy różnicę do zakresu
	// -period/2 .. +period/2, inaczej przekręcenie licznika dawałoby skok
	// w przeciwną stronę - i oś Rz jechała w złym kierunku
	if((period != 0U) && (period < 0x80000000U))
	{
		int32_t half = (int32_t) (period / 2U);

		delta %= (int32_t) period;

		if(delta > half)
		{
			delta -= (int32_t) period; // licznik przekręcił się w dół (0 -> ARR)
		}
		else if(delta < -half)
		{
			delta += (int32_t) period; // licznik przekręcił się w górę (ARR -> 0)
		}
	}

	lastEncoderValue = current;

	return delta;
}

void mouseInit(void)
{
	encoder = __HAL_TIM_GET_COUNTER(&htim2);
	lastEncoderValue = encoder;

	pendingX = 0;
	pendingY = 0;
	pendingRz = 0;
	lastButtons = 0;
	lastReportTick = HAL_GetTick();
}

// Jeden raport HID przenosi jednocześnie obie osie joysticka, oś Rz i przyciski
uint8_t sendAxisReport(int8_t x, int8_t y, int8_t rz, uint8_t buttons)
{
	static uint8_t hid_report[MULTIAXIS_REPORT_SIZE];

	// Pierwszy bajt to numer raportu z deskryptora
	hid_report[0] = MULTIAXIS_REPORT_ID;
	hid_report[1] = (uint8_t) x;
	hid_report[2] = (uint8_t) y;
	hid_report[3] = (uint8_t) rz;
	hid_report[4] = buttons & BUTTONS_MASK;

	return hidSendReport(hid_report, MULTIAXIS_REPORT_SIZE);
}

void processMouseInput(uint8_t buttons)
{
	int32_t xSteps;
	int32_t ySteps;
	int32_t rzSteps;
	int8_t rz;
	uint32_t now;

	// Enkoder odpytujemy w każdym obiegu pętli - licznik TIM2 zawija się co
	// kilkanaście impulsów. Impulsy trafiają do akumulatora, więc żaden krok
	// nie ginie pomiędzy raportami HID.
	pendingRz += readEncoderCounts();
	pendingRz = clampToRange(pendingRz, 127 * ENCODER_COUNTS_PER_STEP);

	now = HAL_GetTick();
	if((now - lastReportTick) < MOUSE_REPORT_INTERVAL_MS)
	{
		return; // jeszcze nie czas na kolejny raport
	}
	lastReportTick = now;

	// Joystick całkujemy w stałych odstępach czasu, więc tempo narastania osi
	// nie zależy od szybkości pętli głównej ani od stanu magistrali USB.
	pendingX += axisToSubpixelMovement(axisX);
	pendingY += axisToSubpixelMovement(axisY);
	pendingX = clampToRange(pendingX, 127 * MOUSE_SUBPIXEL);
	pendingY = clampToRange(pendingY, 127 * MOUSE_SUBPIXEL);

	xSteps = clampToInt8(pendingX / MOUSE_SUBPIXEL);
	ySteps = clampToInt8(pendingY / MOUSE_SUBPIXEL);
	rzSteps = clampToInt8(pendingRz / ENCODER_COUNTS_PER_STEP);

	// Nic się nie zmieniło i nie ma czego zwolnić - nie zaśmiecamy USB
	if((xSteps == 0) && (ySteps == 0) && (rzSteps == 0) && (buttons == lastButtons))
	{
		return;
	}

#if ENCODER_INVERT
	rz = clampToInt8(-rzSteps);
#else
	rz = clampToInt8(rzSteps);
#endif

	// -ySteps, bo ADC rośnie w przeciwną stronę niż oczekiwana oś Y
	if(sendAxisReport(clampToInt8(xSteps), clampToInt8(-ySteps), rz, buttons) != USBD_OK)
	{
		return; // endpoint zajęty - dane zostają w akumulatorach do następnego raportu
	}

	// Z akumulatorów zdejmujemy tylko to, co faktycznie poszło w raporcie
	pendingX -= xSteps * MOUSE_SUBPIXEL;
	pendingY -= ySteps * MOUSE_SUBPIXEL;
	pendingRz -= rzSteps * ENCODER_COUNTS_PER_STEP;
	lastButtons = buttons;
}
