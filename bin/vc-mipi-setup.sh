#!/bin/bash

called_from_service=false
force_create=false

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Setup default ISP tuning files."
    echo "                                                                      "
    echo "Supported actions:                                                    "
    echo " create <w> <h>           Creates or recreates tuning files           "
    echo " init                     Creates tuning files for the detected cam   "
    echo " restart                  Restarts service                            "
    echo "                                                                      "
    echo "Supported action parameters:                                          "
    echo "  <w> <h>                 Image width and height                      "
    echo "                                                                      "
    echo "Supported options:                                                    "
    echo "    --help                Show this help text                         "
    echo "-f, --force               Forces the creation of the tuning files     "
    echo "-s, --service             Set if calling from start_isp_sh            "
}

print() {
    echo ${1} >$(tty)
}

detect_camera_device()
{
    local i2c_bus_addess=$(find /sys/firmware/devicetree/base/soc@0/ -name compatible | \
        grep -oP "[0-9a-f]+(?=/vc_mipi)")
    local i2c_bus_number=$(i2cdetect -l | grep -oP "(?<=i2c-)[0-9]{1,2}(?=.*${i2c_bus_addess})")
    print "Found device tree entry for VC MIPI camera on i2c@${i2c_bus_addess} (i2c-${i2c_bus_number})"

    local device_detected=$(i2cdetect -y -r ${i2c_bus_number} | grep -oP "(?<=10: )10")
    if [[ -n ${device_detected} ]]; then
        print "Detected device with address 0x10 on i2c-${i2c_bus_number}"

        local sensor_type=$(i2cdump -f -y 2 0x10 c 0x10 | grep -oE "(IMX|OV)[0-9]*C?")
        if [[ -n ${sensor_type} ]]; then
            print "Detected device is a VC MIPI ${sensor_type} camera"
            echo ${sensor_type}
        else
            print "Detected device seems not to be a VC MIPI camera"
        fi
    else 
        print "No device detected with adress 0x10 on i2c-${i2c_bus_number}"
    fi
}

create_tuning_files() {
    local width=${1}
    local height=${2}
    local sensor_type=$(detect_camera_device)

    if [[ -n ${sensor_type} ]]; then
        local force=${force_create}

        if [[ -z "${width}" || -z "${height}" ]]; then
            local type=$(echo ${sensor_type} | grep -oE "(IMX|OV)[0-9]*") 
            case "${type}" in
            IMX178) width=3072; height=2048 ;;
            IMX183) width=5440; height=3648 ;;
            IMX226) width=3904; height=3000 ;;
            IMX250) width=2432; height=2048 ;;
            IMX252) width=2048; height=1536 ;;
            IMX264) width=2432; height=2048 ;;
            IMX265) width=2048; height=1536 ;;
            IMX273) width=1440; height=1080 ;;
            IMX290) width=1920; height=1080 ;;
            IMX296) width=1440; height=1080 ;;
            IMX297) width=704;  height=540  ;;
            IMX327) width=1920; height=1080 ;;
            IMX335) width=2592; height=1944 ;;
            IMX392) width=1920; height=1200 ;;
            IMX412) width=4032; height=3040 ;;
            IMX415) width=3840; height=2160 ;;
            IMX462) width=1920; height=1080 ;;
            IMX565) width=4128; height=3000 ;;
            IMX566) width=2848; height=2848 ;;
            IMX567) width=2464; height=2064 ;;
            IMX568) width=2464; height=2064 ;;
            IMX900) width=2048; height=1536 ;;
            IMX900) width=2048; height=1536 ;;
            OV7251) width=640;  height=480  ;;
            OV9281) width=1280; height=800  ;;
            esac
        else 
            force=true
        fi

        local type=$(echo ${sensor_type} | tr '[:upper:]' '[:lower:]')
        local dewarp_file="dewarp_config/vc_${type}_dewarp.json"
        local tuning_file="vc_${type}_tuning.xml"
        local modes_file="vc_mipi_modes.txt"
        
        if [[ ! -e ${dewarp_file} || ! -e ${tuning_file} ]] || $force; then
            print "Image size will be set to ${width}x${height}"

            cd /opt/imx8-isp/bin
            echo "Create ${dewarp_file}"
            sed -e "s/{width}/${width}/g" -e "s/{height}/${height}/g" dewarp_config/vc_mipi_dewarp_template.json > ${dewarp_file}
            echo "Create ${tuning_file}"
            sed -e "s/{width}/${width}/g" -e "s/{height}/${height}/g" vc_mipi_tuning_template.xml > ${tuning_file}

            echo "Create ${modes_file}"
            echo -n "" > ${modes_file}
            echo "[mode.0]" >> ${modes_file}
            echo "xml = \"${tuning_file}\"" >> ${modes_file}
            echo "dwe = \"${dewarp_file}\"" >> ${modes_file}

            restart_service
        else
            print "Tuning files already created. Skip creation!"
        fi
    fi
}

restart_service() {
    if ! ${called_from_service}; then
        systemctl restart imx8-isp
    fi
}

while [ $# != 0 ] ; do
	option="$1"
	shift

	case "${option}" in
    create)
        create_tuning_files ${1} ${2}
        ;;
    -f|--force)
        force_create=true
        ;;
    --help)
		usage
		exit 0
		;;
    init)
        create_tuning_files
        ;;
    restart)
        restart_service
        ;;
    -s|--service)
        called_from_service=true
        ;;
	*)
		echo "Unknown option ${option}"
		exit 1
		;;
	esac
done