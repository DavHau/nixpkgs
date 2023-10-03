{
  config,
  lib,
  extendModules,
  ...
}: {
  imports = [
    ./interface.nix
  ];
  config.public =
    (derivation config.derivation)
    // {
      mix = module: (extendModules {
        modules = [module];
      }).config.public;
    };
}
