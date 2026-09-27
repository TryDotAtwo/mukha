fn main() {
    if std::env::var_os("CARGO_FEATURE_PHOTON").is_some() {
        let path=std::path::PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("build");
        println!("cargo:rustc-link-search=native={}",path.display());
        println!("cargo:rustc-link-lib=dylib=fly_photon");
    }
    if std::env::var_os("CARGO_FEATURE_VISION").is_some() {
        println!("cargo:rerun-if-changed=native/retina.cpp");
        println!("cargo:rerun-if-changed=native/retina.h");
        cc::Build::new().cpp(true).std("c++17").file("native/retina.cpp")
            .flag_if_supported("/fp:strict").flag_if_supported("-ffp-contract=off")
            .compile("fly_retina");
    }
    if std::env::var_os("CARGO_FEATURE_BODY").is_some() {
        let path=std::path::PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("build");
        println!("cargo:rustc-link-search=native={}",path.display());
        println!("cargo:rustc-link-lib=dylib=fly_body");
    }
    println!("cargo:rerun-if-env-changed=FF_CUDA_LIB_DIR");
    if std::env::var_os("CARGO_FEATURE_CUDA").is_some() {
        let path = std::env::var_os("FF_CUDA_LIB_DIR").map(std::path::PathBuf::from)
            .unwrap_or_else(||std::path::PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("build"));
        println!("cargo:rustc-link-search=native={}",path.display());
        let lib=if std::env::var_os("CARGO_FEATURE_CUDA64").is_some(){"fly_cuda64"}else{"fly_cuda_probe"};
        println!("cargo:rustc-link-lib=dylib={lib}");
    }
    println!("cargo:rerun-if-changed=native/lif.cpp");
    println!("cargo:rerun-if-changed=native/lif.h");
    println!("cargo:rerun-if-changed=native/lif_coeff.h");
    cc::Build::new().cpp(true).std("c++17").file("native/lif.cpp")
        .flag_if_supported("/fp:precise").flag_if_supported("-ffp-contract=off")
        .compile("fly_lif");
}
