# Setup hook for pip.
echo "Sourcing pip-install-hook"

declare -a pipInstallFlags

pipInstallPhase() {
    echo "Executing pipInstallPhase"
    runHook preInstall

    sitePackages="@pythonSitePackages@"

    mkdir -p $out/$sitePackages

    echo "checking for private dependencies"
    for dep in $privateRuntimeDeps; do
        echo "installing private dependency: $dep"
        for dir in $(ls $dep/$sitePackages); do
            if [ "$dir" == __pycache__ ] \
                    || [ "$dir" == _site_local ] \
                    || [ -e "$out/$sitePackages/_site_local/$dir" ]; then
                continue
            fi
            mkdir -p $out/$sitePackages/_site_local
            ln -s $dep/$sitePackages/$dir $out/$sitePackages/_site_local/$dir
        done
    done

    export PYTHONPATH="$out/$sitePackages:$PYTHONPATH"

    pushd dist || return 1
    PYTHONPATH="$out/$sitePackages/_site_local:$PYTHONPATH" @pythonInterpreter@ \
        -m pip install ./*.whl \
        --no-index \
        --no-warn-script-location \
        --prefix="$out" \
        --no-cache $pipInstallFlags
    popd || return 1

    runHook postInstall
    echo "Finished executing pipInstallPhase"
}

if [ -z "${dontUsePipInstall-}" ] && [ -z "${installPhase-}" ]; then
    echo "Using pipInstallPhase"
    installPhase=pipInstallPhase
fi
