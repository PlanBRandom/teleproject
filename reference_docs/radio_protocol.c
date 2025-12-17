//All of these commands are for API Mode.  

void RadioSend(unsigned long long address, uint16_t network, uint8_t *data, uint16_t lengthData)
{
  uint8_t packet[];
  int i = 0;
  uint8_t checkSum = 0;
  uint16_t lentgh = 0;  //Length for what goes into packet

  length = 14 + lengthData;

  packet[0]  = 0x7E;
  packet[1]  = (uint8_t)(lentgh >> 8);
  packet[2]  = (uint8_t)length;
  packet[3]  = 0x10;
  packet[4]  = 0x44;
  packet[5]  = (uint8_t)(adress >> 56);  //Destination Address
  packet[6]  = (uint8_t)(adress >> 48);
  packet[7]  = (uint8_t)(adress >> 40);
  packet[8]  = (uint8_t)(adress >> 32);
  packet[9]  = (uint8_t)(adress >> 24);
  packet[10] = (uint8_t)(adress >> 16);
  packet[11] = (uint8_t)(adress >> 8);
  packet[12] = (uint8_t)(adress);
  packet[13] = (uint8_t)(network >> 8);  //Network address
  packet[14] = (uint8_t)(networtk);
  packet[15] = 0;  //Unsued
  packet[16] = 0;  //Unused

  for(i = 3; i <= 16; i++)
  {
     checkSum += packet[i];
  }

  for(i = 17; i <= length + 17; i++)  //Data being sent
  {
     packet[i] = data[i - 17];
     checkSum += packet[i];    
  }
  checkSum = 0xFF - checkSum;  //Checksum calculation, only one byte and subtract from FF
  packet[i] = checkSum;

  length += 4;  //Add in first three bytes and checksum

  WriteRadioUART(packet, length);  
}

void AtCommand(uint16_t command, uint8_t *parameter, uint16_t lengthData)
{
  uint8_t packet[];
  int i = 0;
  uint8_t checkSum = 0;
  uint16_t lentgh = 0;  //Length for what goes into packet

  length = 4 + lengthData;

  packet[0] = 0x7E;
  packet[1] = (lentgh >> 8);
  packet[2] = (uint8_t)(lenght)
  packet[3] = 0x08;
  packet[4] = 0x55;
  packet[5] = (uint8_t)(command >> 8);
  packet[6] = (uint8_t)(command);
  
  for(i = 3; i <= 6; i++)
  {
     checkSum += packet[i];
  }

  for(i = 7; i <= lentgh + 6; i++)
  {
     packet[i] = parameter[i - 7];
     checkSum += packet[i];
  }
  
  checkSum = 0xFF - checkSum;  //Checksum calculation, only one byte and subtract from FF
  packet[i] = checkSum;

  length += 4;  //Add in the first three bytes and the checksum

  WriteRadioUART(packet, length);
}

void WriteRadioUART(uint8_t *packet, length)
{
  int i = 0;
  
  
  for(i = 0; i < length; i++)
  {  
    if(U3MODEbits.PDSEL == 3)
      U3TXREG = packet[i];
    else
      U3TXREG = packet[i] & 0xFF;
  }
}
 



 