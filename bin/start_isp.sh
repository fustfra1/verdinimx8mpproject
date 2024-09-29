#!/bin/sh
#
# Start the isp_media_server in the configuration for Basler daA3840-30mc
#
# (c) Basler 2020
# (c) NXP 2020-2022
#

./vc-mipi-setup.sh --service --create

RUNTIME_DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
NR_DEVICE_TREE_BASLER=$(grep basler-camera-vvcam `find /sys/firmware/devicetree/base/soc@0/ -name compatible | grep i2c` -l | wc -l 2> /dev/null)
NR_DEVICE_TREE_OV5640=$(grep ov5640 `find /sys/firmware/devicetree/base/soc@0/ -name compatible | grep i2c` -l | wc -l 2> /dev/null)
NR_DEVICE_TREE_OS08A20=$(grep os08a20 `find /sys/firmware/devicetree/base/soc@0/ -name compatible | grep i2c` -l | wc -l 2> /dev/null)
NR_DEVICE_TREE_VC_MIPI=$(grep vc_mipi `find /sys/firmware/devicetree/base/soc@0/ -name compatible | grep i2c` -l | wc -l 2> /dev/null)


# check if the basler device has been enabled in the device tree
if [ $NR_DEVICE_TREE_BASLER -eq 1 ]; then

	echo "Starting isp_media_server for Single Basler daA3840-30mc"

	cd $RUNTIME_DIR

	if [ $NR_DEVICE_TREE_OV5640 -eq 0 ]; then

		# Default configuration for Basler daA3840-30mc: basler_4k
		# Available configurations: basler_4k, basler_1080p60, basler_4khdr, basler_1080p60hdr
		exec ./run.sh -c basler_4k -lm

	elif [ $NR_DEVICE_TREE_OV5640 -eq 1 ]; then

		# Default configuration for Basler daA3840-30mc: basler_1080p60
		# Available configurations: basler_1080p60, basler_1080p60hdr
		exec ./run.sh -c basler_1080p60 -lm
	fi

elif [ $NR_DEVICE_TREE_BASLER -eq 2 ]; then

	echo "Starting isp_media_server for Dual Basler daA3840-30mc"

	cd $RUNTIME_DIR
	# Default configuration for Basler daA3840-30mc: dual_basler_1080p60
	# Available configurations: dual_basler_1080p60, dual_basler_1080p60hdr
	exec ./run.sh -c dual_basler_1080p60 -lm

# check if the vc-mipi device has been enabled in the device tree
elif [ $NR_DEVICE_TREE_VC_MIPI -eq 1 ]; then

		echo "Starting isp_media_server for Single VC MIPI CSI-2 camera"

		cd $RUNTIME_DIR
		# Default configuration for VC-MIPI: vc_mipi_single
		# Available configurations: vc_mipi_single
		exec ./run.sh -c vc_mipi_single -lm

elif [ $NR_DEVICE_TREE_VC_MIPI -eq 2 ]; then

		echo "Starting isp_media_server for Dual VC MIPI CSI-2 camera"

		cd $RUNTIME_DIR
		# Default configuration for VC-MIPI: vc_mipi_single
		# Available configurations: vc_mipi_single
		exec ./run.sh -c vc_mipi_dual -lm

# check if the os08a20 device has been enabled in the device tree
elif [ $NR_DEVICE_TREE_OS08A20 -eq 1 ]; then

	echo "Starting isp_media_server for Single os08a20"

	cd $RUNTIME_DIR

	if [ $NR_DEVICE_TREE_OV5640 -eq 0 ]; then

		# Default configuration for Os08a20: Os08a20_4k
		# Available configurations: Os08a20_4k, Os08a20_1080p60, Os08a20_4khdr, Os08a20_1080p30hdr
		exec ./run.sh -c os08a20_4k -lm

	elif [ $NR_DEVICE_TREE_OV5640 -eq 1 ]; then

		# Default configuration for Os08a20: Os08a20_1080p60
		# Available configurations: Os08a20_1080p60, Os08a20_1080p30hdr
		exec ./run.sh -c os08a20_1080p60 -lm
	fi

elif [ $NR_DEVICE_TREE_OS08A20 -eq 2 ]; then

	echo "Starting isp_media_server for Dual os08a20"

	cd $RUNTIME_DIR
	# Default configuration for Os08a20: dual_Os08a20_1080p60
	# Available configurations: dual_Os08a20_1080p60, dual_Os08a20_1080p30hdr
	exec ./run.sh -c dual_os08a20_1080p60 -lm

else
	# no device tree found exit with code no device or address
	echo "No device tree found for Basler camera or os08a20, check dtb file!" >&2
	exit 0
fi
