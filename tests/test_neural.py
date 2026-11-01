import json
import unittest
import numpy as np
from ml.native import ROOT, library, training_features
from ml.train import predict
from ml.train_neural import quantized_predict


class NeuralTests(unittest.TestCase):
    def test_runtime_teacher_features_are_finite_and_bounded(self):
        rng=np.random.default_rng(18)
        clean=rng.normal(0,0.008,16000).astype(np.float32)
        reference=rng.normal(0,0.02,16000).astype(np.float32)
        primary=clean+0.7*np.roll(reference,8)
        x,y=training_features(np.column_stack([primary,reference]),clean)
        self.assertEqual(x.shape,(500,26)); self.assertEqual(y.shape,(500,8))
        self.assertTrue(np.isfinite(x).all() and np.isfinite(y).all())
        self.assertTrue((y>=0.07999).all() and (y<=1).all())

    def test_current_speech_model_matches_exported_json(self):
        lib=library()
        model_id=lib.mounam_model_id().decode()
        candidates=[]
        for path in (ROOT/"models").glob("*model.json"):
            card=json.loads(path.read_text())
            if card.get("model_id")==model_id and "parameters" in card:candidates.append(card)
        self.assertTrue(candidates,"Compiled speech model has no matching provenance JSON.")
        card=candidates[0]
        x=np.random.default_rng(9).uniform(0,1,(200,8)).astype(np.float32)
        x[:,2]=x[:,2]*2-1
        expected=predict(x,[np.asarray(a) for a in card["parameters"]])[1]
        actual=[lib.mounam_predict(np.ascontiguousarray(row)) for row in x]
        np.testing.assert_allclose(actual,expected,atol=3e-6,rtol=3e-5)

    def test_quantized_gain_model_matches_cpp(self):
        lib=library(); model_id=lib.mounam_neural_id().decode()
        if model_id=="untrained":self.skipTest("Neural training has not been imported yet.")
        card=json.loads((ROOT/"models/neural_model.json").read_text())
        self.assertEqual(card["model_id"],model_id)
        x=np.random.default_rng(17).uniform(0,1,(200,26)).astype(np.float32)
        x[:,16:24]=x[:,16:24]*2-1
        expected=quantized_predict(x,card)
        actual=np.empty((len(x),8),np.float32)
        for i,row in enumerate(x):lib.mounam_neural_predict(np.ascontiguousarray(row),actual[i])
        np.testing.assert_allclose(actual,expected,atol=4e-6,rtol=4e-5)
        self.assertTrue((actual>=0.08).all() and (actual<=1).all())


if __name__=="__main__":unittest.main()
