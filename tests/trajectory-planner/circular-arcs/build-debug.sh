#/bin/bash
cd ../../../src
#Ugly way to force rebuild of kinematics, which assumes that tp_debug isn't
#used anywhere else...
touch emc/kinematics/t[cp]*.[ch]
#make EXTRA_DEBUG='-DTC_DEBUG -DTP_DEBUG'
make EXTRA_DEBUG='-DTC_DEBUG -DTP_DEBUG -DTP_INFO_LOGGING'
