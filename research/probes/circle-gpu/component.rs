use crate::*;
use stwo::core::air::{accumulation::PointEvaluationAccumulator, Component};
use stwo::core::circle::CirclePoint;
use stwo::core::constraints::coset_vanishing;
use stwo::core::fields::qm31::SecureField;
use stwo::core::pcs::TreeVec;
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::utils::bit_reverse;
use stwo::core::ColumnVec;
use stwo::prover::backend::cuda::CudaBackend;
use stwo::prover::EvaluationMode;
use stwo::prover::{ComponentProver, DomainEvaluationAccumulator, Trace};
use stwo::stwo_cuda::{base_field_vec::BaseFieldVec, bindings::CudaSecureField, SecureFieldVec};
use stwo_constraint_framework::{FrameworkComponent, FrameworkEval};

pub struct DeviceComponent(pub FrameworkComponent<GateEval>);

impl Component for DeviceComponent {
    fn n_constraints(&self) -> usize {
        self.0.n_constraints()
    }
    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.0.max_constraint_log_degree_bound()
    }
    fn mask_points(
        &self,
        point: CirclePoint<SecureField>,
        bound: u32,
    ) -> TreeVec<ColumnVec<Vec<CirclePoint<SecureField>>>> {
        self.0.mask_points(point, bound)
    }
    fn preprocessed_column_indices(&self) -> Vec<usize> {
        Component::preprocessed_column_indices(&self.0)
    }
    fn trace_log_degree_bounds(&self) -> TreeVec<ColumnVec<u32>> {
        self.0.trace_log_degree_bounds()
    }
    fn evaluate_constraint_quotients_at_point(
        &self,
        point: CirclePoint<SecureField>,
        mask: &TreeVec<ColumnVec<Vec<SecureField>>>,
        accumulator: &mut PointEvaluationAccumulator,
        bound: u32,
    ) {
        self.0
            .evaluate_constraint_quotients_at_point(point, mask, accumulator, bound)
    }
}

extern "C" {
    fn hallmark_gate(
        pre: *const *const u32,
        base: *const *const u32,
        inter: *const *const u32,
        out: *const *const u32,
        powers: *const CudaSecureField,
        denom: *const u32,
        params: *const CudaSecureField,
        log: u32,
        eval_log: u32,
    );
}

impl ComponentProver<CudaBackend> for DeviceComponent {
    fn evaluate_constraint_quotients_on_domain(
        &self,
        trace: &Trace<'_, CudaBackend>,
        accumulator: &mut DomainEvaluationAccumulator<CudaBackend>,
    ) {
        let log = self.0.log_size();
        let EvaluationMode::SubDomain { log_expansion } = accumulator.evaluation_mode() else {
            panic!("unsupported classifier GPU evaluation mode");
        };
        assert_eq!(self.n_constraints(), 9);
        let domain = CanonicCoset::new(log + 1 + log_expansion)
            .circle_domain()
            .split(log_expansion)
            .0;
        let trace_domain = CanonicCoset::new(log);
        let mut inverses: Vec<_> = (0..2)
            .map(|i| coset_vanishing(trace_domain.coset(), domain.at(i)).inverse())
            .collect();
        bit_reverse(&mut inverses);
        let denom = BaseFieldVec::from_vec(inverses);
        let [mut column] = accumulator.columns([(log + 1, self.n_constraints())]);
        column.random_coeff_powers.reverse();
        let powers = SecureFieldVec::from_vec(column.random_coeff_powers);
        let pointers: Vec<Vec<_>> = trace
            .polys
            .iter()
            .map(|tree| tree.iter().map(|p| p.evals.values.device_ptr).collect())
            .collect();
        assert_eq!(
            pointers.iter().map(Vec::len).collect::<Vec<_>>(),
            [11, 4, 12]
        );
        let out = column.col.columns.each_ref().map(|c| c.device_ptr);
        let wires = &self.0.wires.0;
        let params = [
            wires.alpha_powers[0],
            wires.alpha_powers[1],
            wires.z,
            self.0.claimed_sum() / stwo::core::fields::m31::M31::from(1u32 << log),
        ]
        .map(CudaSecureField::from);
        unsafe {
            hallmark_gate(
                pointers[0].as_ptr(),
                pointers[1].as_ptr(),
                pointers[2].as_ptr(),
                out.as_ptr(),
                powers.device_ptr.cast(),
                denom.device_ptr,
                params.as_ptr(),
                log,
                log + 1,
            );
        }
        eprintln!("{{\"schema_id\":\"hallmark.circle-cuda-air/1\",\"gpu_constraint_calls\":1,\"cpu_constraint_fallbacks\":0,\"constraints\":9,\"rows\":{}}}", 1u64 << (log + 1));
    }
}
