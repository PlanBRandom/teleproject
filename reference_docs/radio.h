//*****************************************************************************
//! @file radio.h
//! @author Garrett Friedrichs (garrett.friedrichs@otisinstruments.com)
//! @brief 
//! @version 0.1
//! @date 04-20-2022
//! 
//! @copyright Copyright (c) 2022
//! 
//*****************************************************************************
#ifndef RADIO_H
#define RADIO_H


#include "am_mcu_apollo.h"
#include "am_bsp.h"
#include "am_util.h"
#include "FreeRTOS.h"
#include "task.h"
#include "types.h"
#include "saving.h"
#include "fault.h"

//*****************************************************************************
//                                                                       
//                      TYPEDEFS AND STRUCTURES                                
//                                                                        
//*****************************************************************************

//*****************************************************************************
//
// Custom data type.
// Note - am_uart_buffer was simply derived from the am_hal_iom_buffer macro.
//
//*****************************************************************************
#define am_uart_buffer(A)                                           \
union                                                               \
{                                                                   \
    uint32_t words[(A + 3) >> 2];                                   \
    uint8_t bytes[A];                                               \
}

#define AM_BSP_UART_BUFFER_SIZE     256


union convert32bits {
    float32_t bits32;
    struct twoWords word;
    struct fourBytes by;
};

//*****************************************************************************
//                                                                       
//                      GLOBAL VARIABLES                                   
//                                                                        
//***************************************************************************** 
extern am_hal_uart_config_t sRadioConfig;
extern void *pvRadioUART;

//static uint8_t pui8RadioTxBuffer[AM_BSP_UART_BUFFER_SIZE];
//static uint8_t pui8RadioRxBuffer[AM_BSP_UART_BUFFER_SIZE];



uint8_t RadioReceiveUART(uint8_t* packet, uint8_t length, uint32_t timeout);

#endif 