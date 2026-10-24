/*
 * WS2812B.h
 *
 *  Biblioteka sterowania diodami WS2812B (STM32F431KBT6)
 *  Obsługa jasności, gamma correction oraz DMA w trybie Normal.
 *
 *  Author: Piotr
 *  Date: 14.09.2025
 */

#ifndef INC_WS2812B_H_
#define INC_WS2812B_H_

#include "stm32G4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

#define PI 3.14159265

#define MAX_LED 3
#define USE_BRIGHTNESS 1

void WS2812_Send(void);
void WS2812_SetBrightness(int brightness);
void WS2812_SetLED(int LEDnum, int Red, int Green, int Blue);

void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef *htim);
#endif /* INC_WS2812B_H_ */
