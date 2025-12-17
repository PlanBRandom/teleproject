//*****************************************************************************
//! @file radio.c
//! @author Garrett Friedrichs (garrett.friedrichs@otisinstruments.com)
//! @brief 
//! @version 0.1
//! @date 04-20-2022
//! 
//! @copyright Copyright (c) 2022, Otis Instruments Inc.
//! All rihts reserved
//*****************************************************************************
#include "radio.h"

am_hal_uart_config_t sRadioConfig;
void *pvRadioUART;
//*****************************************************************************
//
// Interrupt handler for the UART.
//
//*****************************************************************************
/*void am_uart1_isr(void)
{
    uint32_t ui32Status;

    //
    // Read the masked interrupt status from the UART.
    //
    am_hal_uart_interrupt_status_get(pvRadioUART, &ui32Status, true);
    am_hal_uart_interrupt_clear(pvRadioUART, ui32Status);
    am_hal_uart_interrupt_service(pvRadioUART, ui32Status, 0);
    
}*/


uint8_t RadioReceiveUART(uint8_t* packet, uint8_t length, uint32_t timeout)
{
    uint32_t ui32BytesRead = 0;
    uint32_t counter = 0, timer = 0;
    
    am_hal_uart_transfer_t sRead = 
    {
        .ui32Direction = AM_HAL_UART_READ,
        .ui32TimeoutMs = 0,
        .pui32BytesTransferred = &ui32BytesRead,
    };
    //counter = 0;

    xSemaphoreTake(xUART_Mutex, portMAX_DELAY);

    while((counter < length) && (timer < (timeout)))
    {
        sRead.pui8Data = &packet[counter];
        sRead.ui32NumBytes = (length - counter);
        am_hal_uart_transfer(pvRadioUART, &sRead);
        am_util_debug_printf("Radio UART: Read %d Bytes\r\n", ui32BytesRead);
        counter += ui32BytesRead;
        vTaskDelay(pdMS_TO_TICKS(10));
        timer+=10;
        am_util_debug_printf("Counter: %d\r\n", counter);
    }

    xSemaphoreGive(xUART_Mutex);
    
#ifdef AM_DEBUG_PRINTF
    if(counter)
    {
        am_util_debug_printf("Radio UART Packet: ");
        for (uint8_t i = 0; i < counter; i++)
        {
            am_util_debug_printf("%d [%X], ", i, packet[i]);
        }
        am_util_debug_printf("\r\n");
    }
#endif
    
    if((uint8_t)counter != length)
    {
        am_util_debug_printf("Timeout: %dms\r\n", timer);
        return 0;
    }
    else
    {
        return 1;
    }
}


