/*
 * Keyboard_defs.c
 *
 *  Created on: Nov 27, 2024
 *      Author: Piotr
 *
 *  Odczyt przyciskow PA2/PA3/PA4 z odklejaniem drgan stykow. Przyciski nie
 *  wysylaja wlasnych raportow - ich bitmaska wchodzi do raportu Multi-axis
 *  (bajt 4), a znaczenie nadaje im aplikacja na PC.
 */

#include "Keyboard_defs.h"
#include "main.h"
#include "gpio.h"

// Opis jednego przycisku: pin oraz bit, który ustawia w raporcie
typedef struct
{
	GPIO_TypeDef *port;
	uint16_t pin;

} buttonDef;

static const buttonDef buttonMap[BUTTONS_COUNT] =
{
	{ BUTTON1_PORT, BUTTON1_PIN },	// bit 0 -> Button 1
	{ BUTTON2_PORT, BUTTON2_PIN },	// bit 1 -> Button 2
	{ BUTTON3_PORT, BUTTON3_PIN }	// bit 2 -> Button 3
};

// Bitmaska wciśniętych przycisków: surowa próbka oraz stan po odklejeniu drgań
static uint8_t buttonsRaw;
static uint8_t buttonsStable;

// Moment ostatniej zmiany surowej próbki
static uint32_t buttonsSampleTick;

// Bitmaska stanu wejść bez filtrowania
static uint8_t sampleButtons(void)
{
	uint8_t state = 0;
	uint8_t i;

	for(i = 0; i < BUTTONS_COUNT; i++)
	{
		GPIO_PinState level = HAL_GPIO_ReadPin(buttonMap[i].port, buttonMap[i].pin);

#if BUTTONS_ACTIVE_LOW
		if(level == GPIO_PIN_RESET)
#else
		if(level == GPIO_PIN_SET)
#endif
		{
			state |= (uint8_t) (1U << i);
		}
	}

	return state;
}

void buttonsInit(void)
{
	buttonsRaw = sampleButtons();
	buttonsStable = buttonsRaw;
	buttonsSampleTick = HAL_GetTick();
}

uint8_t buttonsRead(void)
{
	uint8_t sample = sampleButtons();

	// Stan liczy się dopiero, gdy utrzyma się przez BUTTON_DELAY milisekund -
	// inaczej drgania styku wyglądałyby jak seria wciśnięć
	if(sample != buttonsRaw)
	{
		buttonsRaw = sample;
		buttonsSampleTick = HAL_GetTick();
		return buttonsStable;
	}

	if((HAL_GetTick() - buttonsSampleTick) >= BUTTON_DELAY)
	{
		buttonsStable = sample;
	}

	return buttonsStable;
}
