{ callPackage
# Darwin frameworks
, Cocoa, CoreMedia, VideoToolbox
, ...
}@args:

callPackage ./generic.nix (rec {
  version = "6.0";
  branch = version;
  sha256 = "sha256-R9BicxyfZqeDgONaGarHfOvOzNHHzDCbnII0P/xDDD0=";
  darwinFrameworks = [ Cocoa CoreMedia VideoToolbox ];
} // args)
