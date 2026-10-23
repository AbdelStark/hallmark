use zk_prover::{cli, gadgets::dequant::Variant, layer::Layer, shaperoot::Calibration};

#[test]
fn reconstructed_fold_scales_fit_the_statement() {
    let args: Vec<String> = [
        "compose", "--round", "even", "--variants", "intsplit6", "--table-bits", "16",
        "--s", "32", "--ctx", "128", "--hd", "32", "--head-groups", "2,2",
        "--nin", "128", "--nout", "128", "--residual-stream-a", "32", "--kmax", "16",
        "--synth-residual-stream", "--diagonal-block", "--layout", "zfold",
    ].iter().map(|x| x.to_string()).collect();
    let (original, variant) = cli::layer_of(&args);
    let mut params = cli::params_of(&original, &args, &variant);
    let calibration = Calibration::of(&original);
    for alpha in [9, 0, 7, 14] {
        params.fold_alpha = alpha;
        let rebuilt = Layer::from_params(&params, &calibration);
        let fold = rebuilt.mats.iter().find(|m| m.variant == Variant::Fold).unwrap();
        for t in 0..fold.tokens {
            let gt = fold.fold_gt(t);
            assert!(gt >= i64::from(alpha), "fold token divisor 2^{gt} below alpha {alpha}");
            for c in 0..fold.n_out {
                let gc = fold.fold_gc(c);
                assert!(gc >= 14 - i64::from(alpha), "channel divisor below split");
                assert!(gt + gc >= 14, "divisor below the limb split");
                assert!(gt + gc - 13 <= i64::from(params.fold_rem_bits),
                        "placeholder exceeds the statement's remainder window");
            }
        }
    }
}
