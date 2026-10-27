use hallmark_circle::{read, sha, write, Enrollment, Error, Program};
use std::path::Path;
fn main() -> Result<(), Error> {
    std::env::set_var("RAYON_NUM_THREADS", "4");
    let a: Vec<_> = std::env::args().collect();
    let started = std::time::Instant::now();
    if a.len() == 4 && a[1] == "enroll" {
        let raw = read(Path::new(&a[2]), 256 * 1024 * 1024)?;
        let program: Program = serde_json::from_slice(&raw)?;
        let read_seconds = started.elapsed().as_secs_f64();
        let enrollment = hallmark_circle::prover::enroll(&program, sha(&raw))?;
        let serialization = std::time::Instant::now();
        write(Path::new(&a[3]), &enrollment)?;
        println!(
            "{}",
            serde_json::json!({"schema_id":"hallmark.circle-cli-timing/1", "command":"enroll", "input_parse_seconds":read_seconds, "serialize_write_seconds":serialization.elapsed().as_secs_f64()})
        );
    } else if a.len() == 7 && a[1] == "prove" {
        let raw = read(Path::new(&a[2]), 256 * 1024 * 1024)?;
        let program: Program = serde_json::from_slice(&raw)?;
        let enrollment: Enrollment = serde_json::from_slice(&read(Path::new(&a[3]), 65536)?)?;
        if sha(&raw) != enrollment.program_sha256 {
            return Err("program pin mismatch".into());
        }
        let external: Vec<u32> = serde_json::from_slice(&read(Path::new(&a[4]), 16384)?)?;
        let values: Vec<u32> = serde_json::from_slice(&read(Path::new(&a[5]), 64 * 1024 * 1024)?)?;
        let read_seconds = started.elapsed().as_secs_f64();
        let proof = hallmark_circle::prover::prove(&program, &enrollment, &external, &values)?;
        let serialization = std::time::Instant::now();
        write(Path::new(&a[6]), &proof)?;
        println!(
            "{}",
            serde_json::json!({"schema_id":"hallmark.circle-cli-timing/1", "command":"prove", "input_parse_seconds":read_seconds, "serialize_write_seconds":serialization.elapsed().as_secs_f64()})
        );
    } else {
        return Err("usage: circle-prove enroll program.json enrollment.json | prove program.json enrollment.json public.json witness.json proof.json".into());
    }
    Ok(())
}
