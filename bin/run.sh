#!/bin/sh
#
# Start the isp_media_server in the configuration from user
# (c) NXP 2020-2022
# (c) Basler 2020
#

RUN_SCRIPT=`realpath -s $0`
RUN_SCRIPT_PATH=`dirname $RUN_SCRIPT`
echo "RUN_SCRIPT=$RUN_SCRIPT"
echo "RUN_SCRIPT_PATH=$RUN_SCRIPT_PATH"

LOAD_MODULES="0" # do not load modules, they are automatically loaded if present in /lib/modules
LOCAL_RUN="0" # search modules in /lib/modules and libraries in /usr/lib
RUN_OPTION=""
LOCAL_RUN="0"
# an array with the modules to load, insertion order
declare -a MODULES=("imx8-media-dev" "vvcam-dwe" "vvcam-isp" "vvcam-video")

USAGE="Usage:\n"
USAGE+="run.sh -c <isp_config> &\n"
USAGE+="Supported configurations:\n"
USAGE+="\tbasler_1080p60         - single basler camera on MIPI-CSI1, 1920x1080, 60 fps\n"
USAGE+="\tdual_basler_1080p60    - dual basler cameras on MIPI-CSI1/2, 1920x1080, 60 fps\n"
USAGE+="\tbasler_4k              - single basler camera on MIPI-CSI1, 3840x2160, 30 fps\n"
USAGE+="\tbasler_1080p60hdr      - single basler camera on MIPI-CSI1, 1920x1080, 60 fps, HDR configuration\n"
USAGE+="\tdual_basler_1080p60hdr - dual basler cameras on MIPI-CSI1/2, 1920x1080, 60 fps, HDR configuration\n"
USAGE+="\tbasler_4khdr           - single basler camera on MIPI-CSI1, 3840x2160, 30 fps, HDR configuration\n"

USAGE+="\tos08a20_1080p60         - single os08a20 camera on MIPI-CSI1, 1920x1080, 60 fps\n"
USAGE+="\tdual_os08a20_1080p60    - dual os08a20 cameras on MIPI-CSI1/2, 1920x1080, 60 fps\n"
USAGE+="\tos08a20_4k              - single os08a20 camera on MIPI-CSI1, 3840x2160, 30 fps\n"
USAGE+="\tos08a20_1080p30hdr      - single os08a20 camera on MIPI-CSI1, 1920x1080, 30 fps, HDR configuration\n"
USAGE+="\tdual_os08a20_1080p30hdr - dual os08a20 cameras on MIPI-CSI1/2, 1920x1080, 30 fps, HDR configuration\n"
USAGE+="\tos08a20_4khdr           - single os08a20 camera on MIPI-CSI1, 3840x2160, 15 fps, HDR configuration\n"

USAGE+="\tvc_mipi_single          - single vc-mipi camera on MIPI-CSI1\n"
USAGE+="\tvc_mipi_dual            - dual vc-mipi camera on MIPI-CSI1/2\n"

# parse command line arguments
while [ "$1" != "" ]; do
	case $1 in
		-c | --config )
			shift
			ISP_CONFIG=$1
			;;
		-l | --local )
			LOCAL_RUN="1"
			# search modules and libraries near this script
			# this should work with the flat structure from VSI/Basler
			# but also with the output from make_isp_build_*.sh
			;;
		-lm | --load-modules )
			LOAD_MODULES="1"
			;;
		* )
			echo -e "$USAGE" >&2
			exit 1
	esac
	shift
done

write_default_mode_files () {
	# OS08A20 modes file - only mode 2 is supported
	echo -n "" > OS08A20_MODES.txt
	echo "[mode.0]" >> OS08A20_MODES.txt
	echo "xml = \"OS08a20_8M_10_1080p_linear.xml\"" >> OS08A20_MODES.txt
	echo "dwe = \"dewarp_config/sensor_dwe_os08a20_1080P_config.json\"" >> OS08A20_MODES.txt
	echo "[mode.1]" >> OS08A20_MODES.txt
	echo "xml = \"OS08a20_8M_10_1080p_hdr.xml\"" >> OS08A20_MODES.txt
	echo "dwe = \"dewarp_config/sensor_dwe_os08a20_1080P_config.json\"" >> OS08A20_MODES.txt
	echo "[mode.2]" >> OS08A20_MODES.txt
	echo "xml = \"OS08a20_8M_10_4k_linear.xml\"" >> OS08A20_MODES.txt
	echo "dwe = \"dewarp_config/sensor_dwe_os08a20_4K_config.json\"" >> OS08A20_MODES.txt
	echo "[mode.3]" >> OS08A20_MODES.txt
	echo "xml = \"OS08a20_8M_10_4k_hdr.xml\"" >> OS08A20_MODES.txt
	echo "dwe = \"dewarp_config/sensor_dwe_os08a20_4K_config.json\"" >> OS08A20_MODES.txt

	# Basler DAA3840 modes file
	echo -n "" > DAA3840_MODES.txt
	echo "[mode.0]" >> DAA3840_MODES.txt
	echo "xml = \"DAA3840_30MC_4K-linear.xml\"" >> DAA3840_MODES.txt
	echo "dwe = \"dewarp_config/daA3840_30mc_4K.json\"" >> DAA3840_MODES.txt
	echo "[mode.1]" >> DAA3840_MODES.txt
	echo "xml = \"DAA3840_30MC_1080P-linear.xml\"" >> DAA3840_MODES.txt
	echo "dwe = \"dewarp_config/daA3840_30mc_1080P.json\"" >> DAA3840_MODES.txt
	echo "[mode.2]" >> DAA3840_MODES.txt
	echo "xml = \"DAA3840_30MC_4K-hdr.xml\"" >> DAA3840_MODES.txt
	echo "dwe = \"dewarp_config/daA3840_30mc_4K.json\"" >> DAA3840_MODES.txt
	echo "[mode.3]" >> DAA3840_MODES.txt
	echo "xml = \"DAA3840_30MC_1080P-hdr.xml\"" >> DAA3840_MODES.txt
	echo "dwe = \"dewarp_config/daA3840_30mc_1080P.json\"" >> DAA3840_MODES.txt
}

# write the sensonr config file
write_sensor_cfg_file () {
	local SENSOR_FILE="$1"
	local CAM_NAME="$2"
	local DRV_FILE="$3"
	local MODE_FILE="$4"
	local MODE="$5"

	echo -n "" > $SENSOR_FILE
	echo "name = \"$CAM_NAME\"" >> $SENSOR_FILE
	echo "drv = \"$DRV_FILE\"" >> $SENSOR_FILE
	echo "mode = $MODE" >> $SENSOR_FILE
	cat $MODE_FILE >> $SENSOR_FILE

	if [ ! -f $DRV_FILE ]; then
		echo "File does not exist: $DRV_FILE" >&2
		exit 1
	fi
	if [ ! -f $MODE_FILE ]; then
		echo "File does not exist: $MODE_FILE" >&2
		exit 1
	fi
}

# write the sensonr config file
set_libs_path () {
	local ONE_LIB="$1"
	LIB_PATH=`find $RUN_SCRIPT_PATH -name $ONE_LIB | head -1`
	if [ ! -f "$LIB_PATH" ]; then
		LIB_PATH=`find $RUN_SCRIPT_PATH/../../../usr -name $ONE_LIB | head -1`
		if [ ! -f "$LIB_PATH" ]; then
			echo "$ONE_LIB not found in $RUN_SCRIPT_PATH"
			echo "$ONE_LIB not found in $RUN_SCRIPT_PATH/../../../usr"
			exit 1
		fi
	fi
	LIB_PATH=`realpath $LIB_PATH`
	export LD_LIBRARY_PATH=`dirname $LIB_PATH`:/usr/lib:$LD_LIBRARY_PATH
	echo "LD_LIBRARY_PATH set to $LD_LIBRARY_PATH"
}

load_module () {
	local MODULE="$1.ko"
	local MODULE_PARAMS="$2"

	# return directly if already loaded.
	MODULENAME=`echo $1 | sed 's/-/_/g'`
	echo $MODULENAME
	if lsmod | grep "$MODULENAME" ; then
		echo "$1 already loaded."
		return 0
	fi

	if [ "$LOCAL_RUN" == "1" ]; then
		MODULE_SEARCH=$RUN_SCRIPT_PATH
		MODULE_PATH=`find $MODULE_SEARCH -name $MODULE | head -1`
		if [ "$MODULE_PATH" == "" ]; then
			MODULE_SEARCH=$RUN_SCRIPT_PATH/../../../modules
			MODULE_PATH=`find $MODULE_SEARCH -name $MODULE | head -1`
			if [ "$MODULE_PATH" == "" ]; then
				echo "Module $MODULE not found in $RUN_SCRIPT_PATH"
				echo "Module $MODULE not found in $MODULE_SEARCH"
				exit 1
			fi
		fi
		MODULE_PATH=`realpath $MODULE_PATH`
	else
		MODULE_SEARCH=/lib/modules/`uname -r`/
		MODULE_PATH=`find $MODULE_SEARCH -name $MODULE | head -1`
		if [ "$MODULE_PATH" == "" ]; then
			echo "Module $MODULE not found in $MODULE_SEARCH"
			exit 1
		fi
		MODULE_PATH=`realpath $MODULE_PATH`
	fi
	insmod $MODULE_PATH $MODULE_PARAMS  || exit 1
	echo "Loaded $MODULE_PATH $MODULE_PARAMS"
}

load_modules () {
	# remove any previous instances of the modules
	n=${#MODULES_TO_REMOVE[*]}
	for (( i = n-1; i >= 0; i-- ))
	do
		echo "Removing ${MODULES_TO_REMOVE[i]}..."
		rmmod ${MODULES_TO_REMOVE[i]} &>/dev/null
		#LSMOD_STATUS=`lsmod | grep "${MODULES[i]}"`
		#echo "LSMOD_STATUS=$LSMOD_STATUS"
		if lsmod | grep "${MODULES_TO_REMOVE[i]}" ; then
			echo "Removing ${MODULES_TO_REMOVE[i]} failed!"
			exit 1
		fi
	done

	# and now clean load the modules
	for i in "${MODULES[@]}"
	do
		echo "Loading module $i ..."
		load_module $i
	done
}

write_default_mode_files

echo "Trying configuration \"$ISP_CONFIG\"..."
MODULES_TO_REMOVE=("basler-camera-driver-vvcam" "os08a20" "ov2775" "vc-mipi-vvcam" "${MODULES[@]}")
case "$ISP_CONFIG" in
		basler_4k )
			MODULES=("basler-camera-driver-vvcam" "${MODULES[@]}")
			RUN_OPTION="CAMERA0"
			CAM_NAME="basler-vvcam"
			DRV_FILE="daA3840_30mc.drv"
			MODE_FILE="DAA3840_MODES.txt"
			MODE="0"
			write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			;;
		basler_1080p60 )
			MODULES=("basler-camera-driver-vvcam" "${MODULES[@]}")
			RUN_OPTION="CAMERA0"
			CAM_NAME="basler-vvcam"
			DRV_FILE="daA3840_30mc.drv"
			MODE_FILE="DAA3840_MODES.txt"
			MODE="1"
			write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			;;
		dual_basler_1080p60 )
			MODULES=("basler-camera-driver-vvcam" "${MODULES[@]}")
			RUN_OPTION="DUAL_CAMERA"
			CAM_NAME="basler-vvcam"
			DRV_FILE="daA3840_30mc.drv"
			MODE_FILE="DAA3840_MODES.txt"
			MODE="1"
			write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			write_sensor_cfg_file "Sensor1_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			;;
		basler_4khdr )
			MODULES=("basler-camera-driver-vvcam" "${MODULES[@]}")
			RUN_OPTION="CAMERA0"
			CAM_NAME="basler-vvcam"
			DRV_FILE="daA3840_30mc.drv"
			MODE_FILE="DAA3840_MODES.txt"
			MODE="2"
			write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			;;
		basler_1080p60hdr )
			MODULES=("basler-camera-driver-vvcam" "${MODULES[@]}")
			RUN_OPTION="CAMERA0"
			CAM_NAME="basler-vvcam"
			DRV_FILE="daA3840_30mc.drv"
			MODE_FILE="DAA3840_MODES.txt"
			MODE="3"
			write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			;;
		dual_basler_1080p60hdr )
			MODULES=("basler-camera-driver-vvcam" "${MODULES[@]}")
			RUN_OPTION="DUAL_CAMERA"
			CAM_NAME="basler-vvcam"
			DRV_FILE="daA3840_30mc.drv"
			MODE_FILE="DAA3840_MODES.txt"
			MODE="3"
			write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			write_sensor_cfg_file "Sensor1_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			;;
		 os08a20_4k )
			MODULES=("os08a20" "${MODULES[@]}")
			RUN_OPTION="CAMERA0"
			CAM_NAME="os08a20"
			DRV_FILE="os08a20.drv"
			MODE_FILE="OS08A20_MODES.txt"
			MODE="2"
			write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			;;
		 os08a20_4khdr )
			 MODULES=("os08a20" "${MODULES[@]}")
                         RUN_OPTION="DUAL_CAMERA"
                         CAM_NAME="os08a20"
                         DRV_FILE="os08a20.drv"
                         MODE_FILE="OS08A20_MODES.txt"
                         MODE="3"
                         write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
			 ;;
		 os08a20_1080p60 )
			 MODULES=("os08a20" "${MODULES[@]}")
                         RUN_OPTION="CAMERA0"
                         CAM_NAME="os08a20"
                         DRV_FILE="os08a20.drv"
                         MODE_FILE="OS08A20_MODES.txt"
                         MODE="0"
                         write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         ;;
                 dual_os08a20_1080p60 )
			 MODULES=("os08a20" "${MODULES[@]}")
                         RUN_OPTION="DUAL_CAMERA"
                         CAM_NAME="os08a20"
                         DRV_FILE="os08a20.drv"
                         MODE_FILE="OS08A20_MODES.txt"
                         MODE="0"
                         write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         write_sensor_cfg_file "Sensor1_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         ;;
		 os08a20_1080p30hdr )
			 MODULES=("os08a20" "${MODULES[@]}")
                         RUN_OPTION="CAMERA0"
                         CAM_NAME="os08a20"
                         DRV_FILE="os08a20.drv"
                         MODE_FILE="OS08A20_MODES.txt"
                         MODE="1"
                         write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         ;;
		 dual_os08a20_1080p30hdr )
			 MODULES=("os08a20" "${MODULES[@]}")
                         RUN_OPTION="DUAL_CAMERA"
                         CAM_NAME="os08a20"
                         DRV_FILE="os08a20.drv"
                         MODE_FILE="OS08A20_MODES.txt"
                         MODE="1"
                         write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         write_sensor_cfg_file "Sensor1_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         ;;
		 vc_mipi_single )
                         MODULES=("vc-mipi-vvcam" "${MODULES[@]}")
                         RUN_OPTION="CAMERA0"
                         CAM_NAME="vc-mipi-vvcam"
                         DRV_FILE="vc-mipi.drv"
                         MODE_FILE="vc_mipi_modes.txt"
                         MODE="0"
                         write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         ;;
		 vc_mipi_dual )
                         MODULES=("vc-mipi-vvcam" "${MODULES[@]}")
                         RUN_OPTION="DUAL_CAMERA"
                         CAM_NAME="vc-mipi-vvcam"
                         DRV_FILE="vc-mipi.drv"
                         MODE_FILE="vc_mipi_modes.txt"
                         MODE="0"
                         write_sensor_cfg_file "Sensor0_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         write_sensor_cfg_file "Sensor1_Entry.cfg" $CAM_NAME $DRV_FILE $MODE_FILE $MODE
                         ;;
		 *)
			echo "ISP configuration \"$ISP_CONFIG\" unsupported."
			echo -e "$USAGE" >&2
			exit 1
			;;
	esac

PIDS_TO_KILL=`pgrep -f video_test\|isp_media_server`
if [ ! -z "$PIDS_TO_KILL" ]
then
	echo "Killing preexisting instances of video_test and isp_media_server:"
	echo `ps $PIDS_TO_KILL`
	pkill -f video_test\|isp_media_server
fi

# Need a sure way to wait untill all the above processes terminated
sleep 1

if [ "$LOAD_MODULES" == "1" ]; then
	load_modules
fi

if [ "$LOCAL_RUN" == "1" ]; then
	set_libs_path "libmedia_server.so"
fi

echo "Starting isp_media_server with configuration file $RUN_OPTION"
./isp_media_server $RUN_OPTION

# this should now work
# gst-launch-1.0 -v v4l2src device=/dev/video0 ! "video/x-raw,format=YUY2,width=1920,height=1080" ! queue ! imxvideoconvert_g2d ! waylandsink
# gst-launch-1.0 -v v4l2src device=/dev/video0 ! "video/x-raw,format=YUY2,width=3840,height=2160" ! queue ! imxvideoconvert_g2d ! waylandsink
# gst-launch-1.0 -v v4l2src device=/dev/video0 ! waylandsink
