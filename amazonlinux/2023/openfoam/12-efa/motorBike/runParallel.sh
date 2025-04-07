runParallel()
{
    APP_RUN=
    LOG_IGNORE=false
    LOG_APPEND=false
    LOG_SUFFIX=
    nProcs=$(getNumberOfProcessors)

    # Parse options and executable
    while [ $# -gt 0 ] && [ -z "$APP_RUN" ]; do
        key="$1"
        case "$key" in
            -append|-a)
                LOG_IGNORE=true
                LOG_APPEND=true
                ;;
            -overwrite|-o)
                LOG_IGNORE=true
                ;;
            -suffix|-s)
                LOG_SUFFIX=".$2"
                shift
                ;;
            -np|-n)
                nProcs="$2"
                shift
                ;;
            *)
                APP_RUN="$key"
                APP_NAME="${key##*/}"
                LOG_SUFFIX="${APP_NAME}${LOG_SUFFIX}"
                ;;
        esac

        shift
    done

    if [ -z "$APP_RUN" ]
    then
        echo "Error: application not specified"
        return 1
    fi

    if [ -f log.$LOG_SUFFIX ] && [ "$LOG_IGNORE" = "false" ]
    then
        echo "$APP_RUN already run on $PWD:" \
             "remove log file 'log.$LOG_SUFFIX' to re-run"
    else
        echo "Running $APP_RUN in parallel on $PWD using $nProcs processes"
        if [ "$LOG_APPEND" = "true" ]; then
            (
                mpiexec --allow-run-as-root \
                    -hostfile /app/hostfile \
                    --prefix /opt/openfoam/ThirdParty-12/platforms/linux64Gcc/openmpi-2.1.1 \
                    --display-map \
                    -n ${nProcs} \
                    --mca plm rsh \
                    --mca orte_rsh_agent ssh \
                    --mca btl_tcp_if_include eth0 \
                    --mca btl tcp,self \
                    --mca oob tcp \
                    --mca orte_keep_fqdn_hostnames t \
                    $APP_RUN -parallel "$@" < /dev/null >> log.$LOG_SUFFIX 2>&1
            )
        else
            (
                mpiexec --allow-run-as-root \
                    -hostfile /app/hostfile \
                    --prefix /opt/openfoam/ThirdParty-12/platforms/linux64Gcc/openmpi-2.1.1 \
                    --display-map \
                    -n ${nProcs} \
                    --mca plm rsh \
                    --mca orte_rsh_agent ssh \
                    --mca btl_tcp_if_include eth0 \
                    --mca btl tcp,self \
                    --mca oob tcp \
                    --mca orte_keep_fqdn_hostnames t \
                    $APP_RUN -parallel "$@" < /dev/null >> log.$LOG_SUFFIX 2>&1
            )
        fi
    fi
}
