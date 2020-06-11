from gym.envs.registration import register

register(
    id='TaxiFuel-v0',
    entry_point='gym_taxifuel.envs:TaxiFuelEnv',
)

